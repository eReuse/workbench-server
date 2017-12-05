import json
import locale
from collections import namedtuple
from datetime import timedelta
from json import dumps, loads
from pprint import pformat

from celery import Celery
from celery.utils.log import get_task_logger
from dateutil.parser import parse
from redis import StrictRedis
from requests import ConnectTimeout, ConnectionError, HTTPError, post


class Worker:
    """
    A set of Celery tasks to process, link and upload snapshot events from Workbench clients to DeviceHub.
    :ivar dbs: Redis databases being used.
    """
    Databases = namedtuple('Databases', ('redis', 'consolidated', 'uploaded', 'upload_errors'))

    def __init__(self, host='localhost', json_path='/srv/workbench-data/inventory', first_db: int = 1) -> None:
        """
        Instantiates the tasks, redis and celery. Call to ``start()`` method after to run the celery
        service::

            Worker().start()

        :param host: Where redis resides in.
        :param json_path: Where to save the resulting json files. The worker tries to upload them to a DeviceHub and
        saves them in a file too, so they can be accessed locally easily.
        :param first_db: The first redis database number. We create 5 databases so we will use the next following 5
        redis databases.
        """
        if locale.getpreferredencoding().lower() != 'utf-8':
            raise OSError('Worker needs UTF-8 systems, but yours is {}'.format(locale.getpreferredencoding()))
        self.json_path = json_path
        redisBroker = 'redis://{}:6379/0'.format(host)
        self.queue = Celery('workbench', broker=redisBroker)
        self.queue.conf.update(worker_pool_restarts=True)
        self.dbs = self.instantiate_dbs(host, first_db)
        self.logger = get_task_logger('workbench')

        self.device_hub = {
            'host': 'http://devicehub.ereuse.net',
            'account': {
                'email': 'a@a.a',
                'password': '1234'
            }
        }

        # lambda doesn't work for queue.task
        # todo make this better (like with queue.task()(self.consume_phase))

        @self.queue.task(name='worker.consume_phase')
        def consume_phase(json):
            return self.consume_phase(json)

        @self.queue.task(name='worker.add_usb')
        def add_usb(usb):
            self.logger.info('add usb!')
            return self.add_usb(usb)

        @self.queue.task(name='worker.del_usb')
        def del_usb(usb):
            return self.del_usb(usb)

        @self.queue.task(name='worker.upload_snapshots')
        def upload_snapshots():
            return self.upload_snapshots()

        # Add periodic tasks (in seconds)
        self.queue.add_periodic_task(60, upload_snapshots.s(), name='try to upload every minute')

    @classmethod
    def instantiate_dbs(cls, host: str, first_db: int = 1) -> Databases:
        qty = len(cls.Databases._fields)
        return cls.Databases(*(StrictRedis(host=host, db=db) for db in range(first_db, first_db + qty)))

    def start(self):
        """Initiates the celery service with needed options for running in linux."""
        self.queue.worker_main(['worker', '-B', '-s', '/tmp/workbench-scheduler', '--loglevel=info'])

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

        if 'install_image_ok' in json and 'condition' in aggregated_json:
            # install_image_ok: If we have passed the last phase (if we skipped it counts too)
            # condition: we have linked with the app
            # Then consolidate the json:
            # todo there is no way to consolidate if workbench client dies (ex: stress test did not pass)
            self.consolidate_json(aggregated_json, self.dbs.redis, self.dbs.consolidated, self.json_path)

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
        keys = self.dbs.consolidated.keys('*')
        self.logger.info('{} snapshots to upload.'.format(len(keys)))
        if keys:  # Do we have something to upload?
            try:
                response = post('{}/login'.format(HOST), json=self.device_hub['account'], headers=headers)
                response.raise_for_status()
                account = response.json()
                headers['Authentication'] = 'Basic {}'.format(account['token'])
            except Exception as e:
                self.logger.error('Login error to DeviceHub:\n{}'.format(pformat(e)))
            else:
                for json in self.dbs.consolidated.mget(keys):
                    snapshot = loads(json.decode())
                    _uuid = snapshot['_uuid']
                    del snapshot['device']['_uuid']
                    try:
                        url = '{}/{}/events/devices/snapshot'.format(HOST, account['defaultDatabase'])
                        response = post(url, json=snapshot, headers=headers)
                        response.raise_for_status()
                    except (ConnectionError, ConnectTimeout):
                        # Let's try to upload the snapshot again later
                        self.logger.warning('Snapshot {} to upload later due to connection error'.format(_uuid))
                    except HTTPError:
                        # Error from server, mark the snapshot as erroneous
                        self.logger.error('Snapshot {} saved to upload_errors'.format(_uuid))
                        result_snapshot = response.json()
                        snapshot['_response'] = result_snapshot
                        self.dbs.upload_errors.set(_uuid, json.dumps(snapshot))
                    else:
                        self.logger.info('Snapshot {} correctly uploaded'.format(_uuid))
                        self.dbs.uploaded.set(_uuid, json)
                        self.dbs.consolidated.delete(_uuid)

    @staticmethod
    def consolidate_json(snapshot, redis, consolidated, json_path):
        snapshot['date'] = parse(snapshot.pop('created')).replace(microsecond=0).isoformat()
        snapshot['snapshotSoftware'] = 'Workbench'
        times = snapshot.pop('times')
        snapshot['inventory'] = {
            'elapsed': str(parse(times['iso']) - parse(times['detection'])).split('.')[0]
        }

        save_json = snapshot.pop('save_json')
        snapshot_json = json.dumps(snapshot)
        with open('{}/{}'.format(json_path, save_json['filename']), 'w') as f:
            f.write(snapshot_json)

        redis.delete(snapshot['_uuid'])
        consolidated.set(snapshot['_uuid'], snapshot_json)
