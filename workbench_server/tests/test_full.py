import json
from time import sleep
from unittest.mock import MagicMock

import pytest
from ereuse_utils.test import AUTH, BASIC, Client
from requests_mock import Mocker

from workbench_server.flaskapp import WorkbenchServer
from workbench_server.tests.conftest import jsonf


@pytest.fixture()
def mock_ip(app: WorkbenchServer):
    """Mocks :meth:`workbench_server.info.Info.local_ip`."""
    app.info.local_ip = MagicMock(return_value='X.X.X.X')


@pytest.fixture()
def mock_snapshot_post(request_mock: Mocker) -> (dict, dict, Mocker):
    """
    Mocks uploading to snapshot (login and upload).
    You will need to POST to /login with returned params.
    """
    params = {
        'device-hub': 'https://foo.com',
        'db': 'db-foo'
    }
    headers = {AUTH: BASIC.format('FooToken')}
    request_mock.post('https://foo.com/db-foo/events/devices/snapshot',
                      json={'_id': 'new-snapshot-id'},
                      request_headers=headers)

    return params, headers, request_mock


@pytest.fixture()
def fphases() -> (list, str):
    """Dictionary with the phases."""
    return jsonf('phases'), '/snapshots/181826cf-ab46-4498-bc91-4895c9de5016'


@pytest.fixture()
def fusb() -> (dict, str):
    """Fixture of a plugged-in USB in a Workbench client."""
    return jsonf('usb'), '/usbs/plugged/kingston-0014780ee3fbf090d52f1286-dt_101_g2'


@pytest.mark.usefixtures('mock_ip')
def test_full(client: Client, fphases: (list, str), fusb: (dict, str),
              mock_snapshot_post: (dict, dict, Mocker), app: WorkbenchServer):
    """
    Performs a full success process, emulating Workbench updating
    WorkbenchServer each phase of the process for a computer,
    inserting an USB, linking it and finally uploading it to
    a mocked DeviceHub.
    """
    phases, uri = fphases
    usb, usb_uri = fusb
    dh_params, dh_headers, mocked_snapshot = mock_snapshot_post  # type: dict,dict,Mocker

    # Emptiness, before performing anything
    response, _ = client.get('/info')
    assert response == {
        "attempts": 0,
        "ip": "X.X.X.X",
        "names": [],
        "snapshots": [],
        "usbs": []
    }

    # Let's emulate Workbench submitting snapshot info on every phase
    # Phase 1 (get computer info)
    client.patch(uri, data=phases[0], status=204)
    phase1 = client.get('/info')[0]['snapshots'][0]
    assert phase1['_phases'] == 1
    assert phase1['_totalPhases'] == 4

    # Phase 2 (test hard-drives)
    client.patch(uri, data=phases[1], status=204)
    phase2 = client.get('/info')[0]['snapshots'][0]
    assert phase2['_phases'] == 2

    # Phase 3 (stress test)
    client.patch(uri, data=phases[2], status=204)
    phase3 = client.get('/info')[0]['snapshots'][0]
    assert phase3['_phases'] == 3

    # Phase 4 (erase)
    client.patch(uri, data=phases[3], status=204)
    phase4 = client.get('/info')[0]['snapshots'][0]
    assert phase4['_phases'] == 4

    # todo phase 5 (install OS)

    assert mocked_snapshot.call_count == 0, 'Device shouldn\'t have uploaded as we wait for link'

    # Let's plug an USB
    # As we have finished the phases, plugging the USB will
    # trigger WorkbenchServer to upload to DeviceHub
    # For that to happen, we need first to set DeviceHub connection
    # parameters. Those are passed through /info by DeviceHubClient
    client.get('/info', query=dh_params, headers=dh_headers)
    # Plug USB
    client.post(usb_uri, data=usb, status=204)
    # Link computer
    client.patch(uri, data={'device': {'_id': 'foo-id'}, '_linked': True}, status=204)
    # Give some time to the sender thread
    # to submit it to the mocked DeviceHub
    sleep(1)
    # We sent the snapshot
    assert mocked_snapshot.call_count == 1, 'We should have uploaded the device after linking it'
    # We have created a JSON in the Snapshot folder
    with next(app.snapshots.snapshot_folder.glob('*.json')).open() as f:
        snapshot_file = json.load(f)
    assert snapshot_file['device']['_id'] == 'foo-id'
    assert snapshot_file['device']['serialNumber'] == phases[0]['device']['serialNumber']


def test_full_no_link(client: Client, fphases: (list, str),
                      mock_snapshot_post: (dict, dict, Mocker), app: WorkbenchServer):
    """Like test full but without linking and lesser checks"""
    phases, uri = fphases
    dh_params, dh_headers, mocked_snapshot = mock_snapshot_post  # type: dict,dict,Mocker

    # Set the config

    # This time let's just to the /info before all phases
    # –it doesn't matter
    client.get('/info', query=dh_params, headers=dh_headers)

    config, _ = client.get('/config')
    config['link'] = False
    client.post('/config', data=config, status=204)
    assert not app.configuration.link

    for phase in phases:
        client.patch(uri, data=phase, status=204)
    sleep(1)
    # We sent the snapshot
    assert mocked_snapshot.call_count == 1
    # We have created a JSON in the Snapshot folder
    with next(app.snapshots.snapshot_folder.glob('*.json')).open() as f:
        snapshot_file = json.load(f)
    assert '_id' not in snapshot_file['device'], 'There is no _id because we didn\'t link it'
    assert snapshot_file['device']['serialNumber'] == phases[0]['device']['serialNumber']
