from collections import namedtuple
from datetime import timedelta
from json import dumps, loads
from pprint import pprint

from celery import Celery
from dateutil.parser import parse
from redis import StrictRedis
from requests import ConnectTimeout, ConnectionError, HTTPError, post


class Worker:
    """
    A set of Celery tasks to process, link and upload snapshot events from Workbench clients to DeviceHub.
    :ivar dbs: Redis databases being used.
    """
    Databases = namedtuple('Databases', ('redis', 'usb', 'consolidated', 'uploaded', 'upload_errors'))

    def __init__(self, host='192.168.2.2', json_path='/srv/ereuse-data/inventory', first_db: int = 1) -> None:
        """
        :param host: Where redis resides in.
        :param json_path: Where to save the resulting json files. The worker tries to upload them to a DeviceHub and
        saves them in a file too, so they can be accessed locally easily.
        :param first_db: The first redis database number. We create 5 databases so we will use the next following 5
        redis databases.
        """
        self.json_path = json_path
        redisBroker = 'redis://{}:6379/0'.format(host)
        queue = Celery('workbench', broker=redisBroker)
        queue.conf.update(worker_pool_restarts=True)
        queue.conf.beat_schedule = {
            'try-to-upload': {
                'task': 'worker.upload_snapshots',
                'schedule': 1.0 * 5
            }
        }
        self.dbs = self.Databases(*(StrictRedis(host=host, db=db) for db in range(first_db, first_db + 5)))
        self.device_hub = {
            'host': 'http://devicehub.ereuse.net',
            'account': {
                'email': 'a@a.a',
                'password': '1234'
            }
        }

        # lambda doesn't work for queue.task
        # todo make this better (like with queue.task()(self.consume_phase))

        @queue.task
        def consume_phase(json):
            return self.consume_phase(json)

        @queue.task
        def add_usb(usb):
            return self.add_usb(usb)

        @queue.task
        def del_usb(usb):
            return self.del_usb(usb)

        @queue.task
        def tag_computer(json):
            return self.tag_computer(json)

        @queue.task
        def upload_snapshots():
            return self.upload_snapshots()

    def consume_phase(self, json):
        """
        Processes a snapshot accordingly of the phase is it in, completing it with computed values, etc.

        Workbench sends the snapshot to WorkbenchServer after completing a phase, for example after testing
        the hard-drives, as a way to ensure being able to generate a snapshot even if the workbench dies in the
        process, for example because a test hanged or stopped the machine.

        This method receives each phase and processes the partial snapshot.

        Phases are as follows:

        0. Initial snapshot with hardware information and identifiers.
        1. Benchmark hard drives.
        2. More tests?
        3. Copy to usb?
        4. Stress test.
        5. OS installation.
        """
        json = loads(json)

        _uuid = json['device']['_uuid']

        aggregated_json = self.dbs.redis.get(_uuid)
        if aggregated_json is not None:
            aggregated_json = loads(aggregated_json.decode())

        if aggregated_json is None:  # phase 0 (initial detection)
            aggregated_json = json
            aggregated_json['times'] = {'detection': json['created']}
        elif 'components' in json:  # phase 1 (hdd test)
            aggregated_json['times']['hd_benchmark'] = json['created']
        elif 'localpath' in json:  # phase 2 (first test results)
            aggregated_json['times']['save_json'] = json['created']
            aggregated_json['save_json'] = {
                'localpath': json['localpath'],
                'filename': json['filename'],
                'signed_data': json['signed_data']
            }
        elif 'copy_to_usb' in json:  # phase 3 (copy to usb)
            aggregated_json['times']['copy_to_usb'] = json['created']
        elif 'stress_test_ok' in json:
            # phase 4 (stress test) only if the stress has been successful
            if 'tests' not in aggregated_json:
                aggregated_json['tests'] = []
            aggregated_json['times']['hd_stress_test'] = json['created']
            aggregated_json['tests'].append({
                '@type': 'StressTest',
                'success': json['stress_test_ok'],
                'elapsed': str(timedelta(minutes=json['stress_test_mins']))
            })
        elif 'install_image_ok' in json:  # phase 5 (os install)
            elapsed = str(parse(json['created']) - parse(aggregated_json['times']['hd_stress_test'])).split('.')[0]
            aggregated_json['times']['iso'] = json['created']
            aggregated_json['osInstallation'] = {
                'label': json['image_name'],
                'success': json['install_image_ok'],
                'elapsed': elapsed
            }

        self.dbs.redis.set(_uuid, dumps(aggregated_json))

        if len(aggregated_json['times'].keys()) > 5 and 'condition' in aggregated_json:
            self._consolidate_json(aggregated_json)

    def add_usb(self, usb):
        inventory = usb.pop('inventory')
        self.dbs.usb.set(inventory, dumps(usb))

    def del_usb(self, usb):
        self.dbs.usb.delete(usb['inventory'])

    def tag_computer(self, json):
        _uuid = json['_uuid']
        aggregated_json = self.dbs.redis.get(_uuid)
        if aggregated_json is not None:
            aggregated_json = loads(str(aggregated_json, 'utf-8'))

            if 'gid' in json and json['gid']:
                aggregated_json['gid'] = json['gid']
            if '_id' in json and json['_id']:
                aggregated_json['_id'] = json['_id']
            if 'lot' in json and json['lot']:
                aggregated_json['group'] = {'@type': 'Lot', '_id': json['lot']}

            aggregated_json['device']['type'] = json['device_type']
            aggregated_json['condition'] = {
                'appearance': {'general': json['visual_grade']},
                'functionality': {'general': json['functional_grade']}
            }

            if json['comment']:
                aggregated_json['comment'] = json['comment']

            self.dbs.redis.set(_uuid, dumps(aggregated_json))

            if len(aggregated_json['times'].keys()) > 5:
                self._consolidate_json(aggregated_json)

    def upload_snapshots(self):
        """
        a connection error, like being offline, but not when receiving an erroneous HTTP exception (ej 422).
        Upload the Snapshots to a DeviceHub. This task will retry re-uploading snapshots in case of
        """
        HOST = self.device_hub['host']
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        try:
            response = post('{}/login'.format(HOST), json=self.device_hub['account'], headers=headers)
            response.raise_for_status()
            account = response.json()
            headers['Authentication'] = 'Basic {}'.format(account['token'])
        except Exception as e:
            pprint(e)
        else:
            for json in self.dbs.consolidated.mget(self.dbs.consolidated.keys('*')):
                snapshot = loads(json.decode())
                _uuid = snapshot['_uuid']
                del snapshot['device']['_uuid']
                try:
                    url = '{}/{}/events/devices/snapshot'.format(HOST, account['defaultDatabase'])
                    response = post(url, json=snapshot, headers=headers)
                    response.raise_for_status()
                except (ConnectionError, ConnectTimeout) as e:
                    # Let's try to upload the snapshot again later
                    pprint(e)
                except HTTPError as e:
                    # Error from server, mark the snapshot as erroneous
                    pprint(e)
                    result_snapshot = response.json()
                    self.dbs.upload_errors.set(_uuid, {'json': json, 'response': result_snapshot})
                else:
                    self.dbs.uploaded.set(_uuid, json)
                    self.dbs.consolidated.delete(_uuid)

    def _consolidate_json(self, json):
        json['date'] = parse(json['created']).replace(microsecond=0).isoformat()
        del json['created']
        json['snapshotSoftware'] = 'Workbench'
        json['inventory'] = {
            'elapsed': str(parse(json['times']['iso']) - parse(json['times']['detection'])).split('.')[0]
        }
        del json['times']

        dumped = None
        if 'save_json' in json:
            filename = json['save_json']['filename']
            del json['save_json']

            dumped = dumps(json)
            with open('{}/{}'.format(self.json_path, filename), 'w') as f:
                f.write(dumped)

        self.dbs.redis.delete(json['_uuid'])
        self.dbs.consolidated.set(json['_uuid'], dumped or dumps(json))
