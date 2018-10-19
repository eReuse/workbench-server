import json
from time import sleep

import pytest
from ereuse_utils.test import Client
from requests_mock import Mocker

from tests.conftest import jsonf
from workbench_server.flaskapp import WorkbenchServer


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
    s = jsonf('full-snapshot')
    usb, usb_uri = fusb
    dh_params, dh_headers, mocked_snapshot = mock_snapshot_post

    # Emptiness, before performing anything
    response, _ = client.get('/info')
    assert response == {
        "attempts": 0,
        "ip": "X.X.X.X",
        "snapshots": [],
        "usbs": []
    }

    # Let's emulate Workbench submitting snapshot info on every phase
    # Phase 1 (get computer info)
    client.patch('snapshots/', item=s['uuid'], data=s, status=204)
    client.get('/info')

    s['_phase'] = "Foo"
    client.patch('snapshots/', item=s['uuid'], data=s, status=204)
    client.get('/info')

    s['_phase'] = "Bar"
    client.patch('snapshots/', item=s['uuid'], data=s, status=204)
    client.get('/info')

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
    client.patch('snapshots/',
                 item=s['uuid'],
                 data={
                     'device': {
                         'tags': [{'id': 'foo-tag', 'type': 'Tag'}],
                         'events': [{
                             'type': 'WorkbenchRate',
                             'appearance': 'E',
                             'bios': 'A',
                             'functionality': 'B'
                         }]
                     }
                 },
                 status=204)
    sleep(0.2)
    i, _ = client.get('/info', query=dh_params, headers=dh_headers)
    assert i['snapshots'][0]['_uploaded'] == 'new-snapshot-id'
    assert i['snapshots'][0]['_actualPhase'] == 'Done'
    assert i['snapshots'][0]['_phase'] == 'Bar'
    # Give some time to the sender thread
    # to submit it to the mocked DeviceHub
    # We sent the snapshot
    assert mocked_snapshot.call_count == 1, 'We should have uploaded the device after linking it'
    # We have created a JSON in the Snapshot folder
    with next(app.folder.joinpath('Snapshots').glob('*.json')).open() as f:
        snapshot_file = json.load(f)
    assert snapshot_file['device']['tags'] == [{'id': 'foo-tag', 'type': 'Tag'}]
    assert len(snapshot_file['device']['events']) == 2
    assert snapshot_file['device']['serialNumber'] == 'LXAZ70X0669112B8DB1601'


def test_full_no_link(client: Client,
                      mock_snapshot_post: (dict, dict, Mocker),
                      app: WorkbenchServer):
    """Like test full but without linking and lesser checks"""

    s = jsonf('full-snapshot')
    dh_params, dh_headers, mocked_snapshot = mock_snapshot_post

    # Set the config

    # This time let's just to the /info before all phases
    # –it doesn't matter
    client.get('/info', query=dh_params, headers=dh_headers)

    config, _ = client.get('/config')
    # todo readd this when user can remove link with config config['link'] = False
    client.post('/config', data=config, status=204)
    # assert not app.configuration.link
    app.configuration.link = False

    s['_phase'] = 'Bar'
    client.patch('snapshots/', item=s['uuid'], data=s, status=204)
    sleep(0.1)
    # We sent the snapshot
    assert mocked_snapshot.call_count == 1
    # We have created a JSON in the Snapshot folder
    with next(app.folder.joinpath('Snapshots').glob('*.json')).open() as f:
        snapshot_file = json.load(f)
    assert 'tags' not in snapshot_file, 'No tag as we did not link it'
