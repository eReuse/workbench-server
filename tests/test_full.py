import json
from time import sleep

import pytest
from ereuse_utils.naming import Naming
from ereuse_utils.test import Client
from furl import furl
from requests_mock import Mocker

from tests.conftest import jsonf
from workbench_server.flaskapp import WorkbenchServer
from workbench_server.settings import DevicehubConnection


@pytest.mark.usefixtures('mock_ip')
def test_full(client: Client,
              fusb: (dict, str),
              mock_snapshot_post: (dict, dict, Mocker),
              app: WorkbenchServer):
    """
    Performs a full success process, emulating Workbench updating
    WorkbenchServer each phase of the process for a computer,
    inserting an USB, linking it and finally uploading it to
    a mocked DeviceHub.
    """


@pytest.mark.usefixtures('mock_ip')
def test_full_no_link(client: Client,
                      app: WorkbenchServer):
    """Like test full but without linking and lesser checks"""
    d = 'fixtures/wb'
    info = jsonf(dir=d, name='info')

    uuid = info['uuid']
    url = '/snapshots/{}'.format(uuid)
    ev_d = url + '/device/action/'
    ev_c = url + '/components/{}/action/'
    i = '/info/'
    progress = '/snapshots/{}/progress/'.format(uuid)

    cpu = 3
    cpu_url = ev_c.format(cpu)

    hdd1 = 2
    hdd1_url = ev_c.format(hdd1)
    hdd2 = 4
    hdd2_url = ev_c.format(hdd2)

    client.post(url, info, status=204)
    x, _ = client.get(i)
    assert len(x['snapshots']) == 1
    assert x['snapshots'][0]['uuid'] == uuid
    assert x['snapshots'][0]['_phase'] == 'Info'

    # Benchmarks actions
    b1 = jsonf(dir=d, name='benchmark-processor')
    client.post(cpu_url, b1, status=204)
    x, _ = client.get(i)
    assert x['snapshots'][0]['_phase'] == 'Benchmark'
    assert len(x['snapshots'][0]['components'][cpu]['actions'])

    b2 = jsonf(dir=d, name='benchmark-processor-sysbench')
    client.post(cpu_url, b2, status=204)
    x, _ = client.get(i)
    assert x['snapshots'][0]['_phase'] == 'Benchmark'

    b3 = jsonf(dir=d, name='benchmark-ram')
    client.post(ev_d, b3, status=204)
    x, _ = client.get(i)
    assert x['snapshots'][0]['_phase'] == 'Benchmark'

    # Benchmark data storage for both hdds
    bds = jsonf(dir=d, name='benchmark-data-storage')
    client.post(hdd1_url, b2, status=204)
    x, _ = client.get(i)
    assert x['snapshots'][0]['_phase'] == 'Benchmark'

    bds['logicalName'] = 'dev/sdb'
    client.post(hdd2_url, b2, status=204)
    x, _ = client.get(i)
    assert x['snapshots'][0]['_phase'] == 'Benchmark'

    # Stress progress
    stress = jsonf(dir=d, name='stress.progress')
    client.post(progress, stress, status=204)
    x, _ = client.get(i)
    assert x['snapshots'][0]['_phase'] == 'StressTest'

    stress['percentage'] = 50
    client.post(progress, stress, status=204)
    x, _ = client.get(i)
    assert x['snapshots'][0]['_phase'] == 'StressTest'

    # StressTest action
    client.post(ev_d, jsonf(dir=d, name='stress'), status=204)
    x, _ = client.get(i)
    assert x['snapshots'][0]['_phase'] == 'StressTest'

    # smart progress
    smart = jsonf(dir=d, name='smart.progress')
    smart['component'] = hdd1

    client.post(progress, smart, status=204)  # progess of smart 1 of hdd 1
    x, _ = client.get(i)
    assert x['snapshots'][0]['_phase'] == 'DataStorage'

    smart['component'] = hdd2
    client.post(progress, smart, status=204)  # progess of smart 1 of hdd 2
    x, _ = client.get(i)
    assert x['snapshots'][0]['_phase'] == 'DataStorage'

    smart['percentage'] = 80
    smart['component'] = hdd1
    client.post(progress, smart, status=204)  # progess of smart 2 of hdd 1
    x, _ = client.get(i)
    assert x['snapshots'][0]['_phase'] == 'DataStorage'

    smart['component'] = hdd2
    client.post(progress, smart, status=204)  # progess of smart 2 of hdd 2
    x, _ = client.get(i)
    assert x['snapshots'][0]['_phase'] == 'DataStorage'

    # smart action
    smart = jsonf(dir=d, name='smart')
    client.post(hdd1_url, smart, status=204)
    x, _ = client.get(i)
    assert x['snapshots'][0]['_phase'] == 'DataStorage'

    smart['assessment'] = False
    client.post(hdd2_url, smart, status=204)
    x, _ = client.get(i)
    assert x['snapshots'][0]['_phase'] == 'DataStorage'

    # erase progress
    erase = jsonf(dir=d, name='erase.progress')
    erase['component'] = hdd1

    client.post(progress, erase, status=204)
    x, _ = client.get(i)
    assert x['snapshots'][0]['_phase'] == 'DataStorage'

    erase['component'] = hdd2
    client.post(progress, erase, status=204)
    x, _ = client.get(i)
    assert x['snapshots'][0]['_phase'] == 'DataStorage'

    erase['percentage'] = 80
    erase['component'] = hdd1
    client.post(progress, erase, status=204)
    x, _ = client.get(i)
    assert x['snapshots'][0]['_phase'] == 'DataStorage'

    erase['component'] = hdd2
    client.post(progress, erase, status=204)
    x, _ = client.get(i)
    assert x['snapshots'][0]['_phase'] == 'DataStorage'

    # Erase action
    erase = jsonf(dir=d, name='erase')
    client.post(hdd1_url, erase, status=204)
    x, _ = client.get(i)
    assert x['snapshots'][0]['_phase'] == 'DataStorage'

    erase['severity'] = 'Error'
    client.post(hdd2_url, erase, status=204)
    x, _ = client.get(i)
    assert x['snapshots'][0]['_phase'] == 'DataStorage'

    # install
    install = jsonf(dir=d, name='install.progress')
    install['component'] = hdd1

    client.post(progress, install, status=204)
    x, _ = client.get(i)
    assert x['snapshots'][0]['_phase'] == 'DataStorage'

    install['component'] = hdd2
    client.post(progress, install, status=204)
    x, _ = client.get(i)
    assert x['snapshots'][0]['_phase'] == 'DataStorage'

    install['percentage'] = 80
    install['component'] = hdd1
    client.post(progress, install, status=204)
    x, _ = client.get(i)
    assert x['snapshots'][0]['_phase'] == 'DataStorage'

    install['component'] = hdd2
    client.post(progress, install, status=204)
    x, _ = client.get(i)
    assert x['snapshots'][0]['_phase'] == 'DataStorage'

    # Install action
    install = jsonf(dir=d, name='install')
    client.post(hdd1_url, install, status=204)
    x, _ = client.get(i)
    assert x['snapshots'][0]['_phase'] == 'DataStorage'

    install['severity'] = 'Error'
    client.post(hdd2_url, install, status=204)
    x, _ = client.get(i)
    assert x['snapshots'][0]['_phase'] == 'DataStorage'

    # Last submission with full snapshot
    closed_action = jsonf(dir=d, name='closed')
    client.patch(url, closed_action, status=204)

    d = info['device']
    x, _ = client.get(i)
    assert x['snapshots'][0]['closed']
    # We have not sent dh info yet
    assert x['snapshots'][0]['_phase'] == 'ReadyToUpload'

    hid = Naming.hid(d['type'], d['manufacturer'], d['model'], d['serialNumber']) + '.json'
    with app.dir.snapshots.joinpath(hid).open() as f:
        x = json.load(f)
    assert x['closed']

    # Send devicehub information so manager can post the action
    x, _ = client.get(i, query=[('devicehub', 'https://foo.com'), ('db', 'bar'),
                                ('token', 'e376fc02-d312-4ea4-8f12-23d7eb4730ff')])
    with app.app_context():
        connection_settings = DevicehubConnection.read()
    assert connection_settings.devicehub == furl('https://foo.com')
    assert connection_settings.db == 'bar'
    assert connection_settings.token == 'e376fc02-d312-4ea4-8f12-23d7eb4730ff'

    sleep(1.2)  # Allow Manager to take action

    x, _ = client.get(i)
    snapshot = x['snapshots'][0]
    assert snapshot['_phase'] == 'Uploaded'
    assert snapshot['id'] == 'new-snapshot-id'  # The result of the mock

    with app.dir.snapshots.joinpath(hid).open() as f:
        x = json.load(f)
    assert x['id'] == 'new-snapshot-id'
