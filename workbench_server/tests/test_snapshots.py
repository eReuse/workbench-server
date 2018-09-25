import pytest
from ereuse_utils.test import Client

from workbench_server.tests.conftest import jsonf
from workbench_server.views.snapshots import Snapshot


def test_snapshots_snapshot_closed():
    s = Snapshot()
    # We don't expect any event, so it will be closed when linked
    s['expectedEvents'] = []
    s['_phase'] = 0
    assert not s.closed(wait_for_link=True)
    assert s.closed(wait_for_link=False)

    # We expect an event, so it will be closed when event1 and linked
    s['expectedEvents'] = ['event1']
    assert not s.closed(wait_for_link=True)
    assert not s.closed(wait_for_link=False)
    s['_phase'] = "event1"
    assert s.closed(wait_for_link=False)
    s['tags'] = ['foo-bar']
    assert s.closed(wait_for_link=True)


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
