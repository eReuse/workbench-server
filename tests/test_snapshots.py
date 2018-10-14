import pytest
from ereuse_utils.test import Client

from tests.conftest import jsonf, phase
from workbench_server.views.snapshots import Snapshot


def test_snapshots_snapshot_closed():
    s = Snapshot()
    # We don't expect any event, so it will be closed when linked
    s['closed'] = True
    assert not s.ready_to_upload(wait_for_link=True)
    assert s.ready_to_upload(wait_for_link=False)

    # We expect an event, so it will be closed when event1 and linked
    s['closed'] = False
    assert not s.ready_to_upload(wait_for_link=True)
    assert not s.ready_to_upload(wait_for_link=False)
    s['closed'] = True
    s['device']['tags'] = ['foo-bar']
    assert s.ready_to_upload(wait_for_link=True)


def test_snapshot_merger():
    s = Snapshot()
    s['x'] = [1, 2, 3]
    s['closed'] = False
    s['uuid'] = s['device'] = s['expectedEvents'] = s['_phase'] = 'something'
    s.merge({'x': [1, 4, 5]})
    assert s['x'] == [1, 2, 3, 4, 5]
    s['x'] = [{'type': 'foo'}, {'type': 'bar'}]
    s.merge({'x': [{'type': 'foo'}, {'type': 'foo'}, {'type': 'barz'}]})
    assert s['x'] == [{'type': 'foo'}, {'type': 'bar'}, {'type': 'barz'}]


@pytest.mark.usefixtures('mock_ip')
def test_snapshots_snapshot_view(client: Client):
    s = jsonf('mini-snapshot')
    client.patch('snapshots/', item=s['uuid'], data=s, status=204)
    d, _ = client.get('info')
    assert d['snapshots'][0]['uuid'] == s['uuid']
    s['an update'] = True
    client.patch('snapshots/', item=s['uuid'], data=s, status=204)
    d, _ = client.get('info')
    assert d['snapshots'][0]['uuid'] == s['uuid']
    assert d['snapshots'][0]['an update'] is True


@pytest.mark.usefixtures('mock_ip')
def test_snapshots_phases(client: Client):
    i = phase('info')
    client.patch('snapshots/', item=i['uuid'], data=i, status=204)
    d, _ = client.get('info')
    assert d['snapshots'][0]['_actualPhase'] == 'Benchmark'

    i = phase('benchmark')
    client.patch('snapshots/', item=i['uuid'], data=i, status=204)
    d, _ = client.get('info')
    assert d['snapshots'][0]['_actualPhase'] == 'TestDataStorage'

    i = phase('data')
    client.patch('snapshots/', item=i['uuid'], data=i, status=204)
    d, _ = client.get('info')
    assert d['snapshots'][0]['_actualPhase'] == 'StressTest'

    i = phase('stress')
    client.patch('snapshots/', item=i['uuid'], data=i, status=204)
    d, _ = client.get('info')
    assert d['snapshots'][0]['_actualPhase'] == 'EraseBasic'

    i = phase('erase')
    client.patch('snapshots/', item=i['uuid'], data=i, status=204)
    d, _ = client.get('info')
    assert d['snapshots'][0]['_actualPhase'] == 'Link'
