from datetime import timedelta
from json import dumps, loads
from pprint import pprint

from celery import Celery
from dateutil.parser import parse
from redis import StrictRedis
from requests import ConnectTimeout, ConnectionError, HTTPError, post

# from celery.utils.log import get_task_logger
from auth import DeviceHubAuth

# serverIP = 'localhost'

serverIP = '192.168.2.2'

# json_path = './jsons'
json_path = '/srv/ereuse-data/inventory'

redisBroker = 'redis://{}:6379/0'.format(serverIP)

device_hub = {
    'domain': 'http://devicehub.ereuse.net',
    'account': {
        'email': 'a@a.a',
        'password': '1234'
    }
}
device_hub_auth = DeviceHubAuth(**device_hub)

queue = Celery('workbench', broker=redisBroker)
queue.conf.update(worker_pool_restarts=True)
redis = StrictRedis(host=serverIP, db=1)
redis_usb = StrictRedis(host=serverIP, db=2)
redis_consolidated = StrictRedis(host=serverIP, db=3)
redis_uploaded = StrictRedis(host=serverIP, db=4)
redis_uploaderrors = StrictRedis(host=serverIP, db=5)

# log = get_task_logger(__name__)

queue.conf.beat_schedule = {
    'try-to-upload': {
        'task': 'worker.upload_jsons',
        'schedule': 1.0 * 5
    }
}


@queue.task
def consume_phase(json):
    if isinstance(json, str):
        json = loads(json)

    _uuid = json['device']['_uuid']

    aggregated_json = redis.get(_uuid)
    if aggregated_json is not None:
        aggregated_json = loads(str(aggregated_json, 'utf-8'))

    if aggregated_json is None:
        aggregated_json = json
        aggregated_json['times'] = {'detection': json['created']}
    elif 'components' in json:
        aggregated_json['times']['hd_benchmark'] = json['created']
    elif 'localpath' in json:
        aggregated_json['times']['save_json'] = json['created']
        aggregated_json['save_json'] = {
            'localpath': json['localpath'],
            'filename': json['filename'],
            'signed_data': json['signed_data']
        }
    elif 'copy_to_usb' in json:
        aggregated_json['times']['copy_to_usb'] = json['created']
    elif 'stress_test_ok' in json:
        if 'tests' not in aggregated_json:
            aggregated_json['tests'] = []
        aggregated_json['times']['hd_stress_test'] = json['created']
        aggregated_json['tests'].append({
            '@type': 'StressTest',
            'success': json['stress_test_ok'],
            'elapsed': str(timedelta(minutes=json['stress_test_mins']))
        })
    elif 'install_image_ok' in json:
        elapsed = str(parse(json['created']) - parse(aggregated_json['times']['hd_stress_test'])).split('.')[0]
        aggregated_json['times']['iso'] = json['created']
        aggregated_json['osInstallation'] = {
            'label': json['image_name'],
            'success': json['install_image_ok'],
            'elapsed': elapsed
        }

    redis.set(_uuid, dumps(aggregated_json))

    if len(aggregated_json['times'].keys()) > 5 and 'condition' in aggregated_json:
        consolidate_json(aggregated_json)


def consolidate_json(json):
    json['date'] = parse(json['created']).replace(microsecond=0).isoformat()
    del json['created']
    json['snapshotSoftware'] = 'Workbench'
    json['inventory'] = {'elapsed': str(parse(json['times']['iso']) - parse(json['times']['detection'])).split('.')[0]}
    del json['times']

    dumped = None
    if 'save_json' in json:
        filename = json['save_json']['filename']
        del json['save_json']

        dumped = dumps(json)
        with open('{}/{}'.format(json_path, filename), 'w') as f:
            f.write(dumped)

    redis.delete(json['_uuid'])
    redis_consolidated.set(json['_uuid'], dumped or dumps(json))


@queue.task
def add_usb(usb):
    inventory = usb.pop('inventory')
    redis_usb.set(inventory, dumps(usb))


@queue.task
def del_usb(usb):
    redis_usb.delete(usb['inventory'])


@queue.task
def tag_computer(json):
    _uuid = json['_uuid']
    aggregated_json = redis.get(_uuid)
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

        redis.set(_uuid, dumps(aggregated_json))

        if len(aggregated_json['times'].keys()) > 5:
            consolidate_json(aggregated_json)


@queue.task
def upload_jsons():
    DOMAIN = device_hub['domain']
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    try:
        response = post('{}/login'.format(DOMAIN), json=device_hub['account'], headers=headers)
        response.raise_for_status()
        account = response.json()
        headers['Authentication'] = 'Basic {}'.format(account['token'])
    except Exception as e:
        pprint(e)
    else:
        for json in redis_consolidated.mget(redis_consolidated.keys('*')):
            snapshot = loads(json.decode('utf-8'))
            _uuid = snapshot['_uuid']
            del snapshot['device']['_uuid']
            try:
                url = '{}/{}/events/devices/snapshot'.format(DOMAIN, account['defaultDatabase'])
                response = post(url, json=snapshot, headers=headers)
                response.raise_for_status()
            except (ConnectionError, ConnectTimeout) as e:
                # Let's try to upload the snapshot again later
                pprint(e)
            except HTTPError as e:
                # Error from server, mark the snapshot as erroneous
                pprint(e)
                result_snapshot = response.json()
                redis_uploaderrors.set(_uuid, {'json': json, 'response': result_snapshot})
            else:
                redis_uploaded.set(_uuid, json)
                redis_consolidated.delete(_uuid)
