import json
from collections import OrderedDict
from copy import copy
from pathlib import Path

from ereuse_utils import DeviceHubJSONEncoder
from ereuse_utils.naming import Naming
from ereuse_utils import now
from flask import Response, jsonify, request
from pydash import merge
from requests import HTTPError, Session
from werkzeug.exceptions import NotFound

from workbench_server import flaskapp


class Snapshots:
    """
    Saves incoming snapshots, saving them to a file and uploading them to a DeviceHub when they
    are completed (all phases done and linked).
    """

    def __init__(self, app: 'flaskapp.WorkbenchServer', public_folder: Path) -> None:
        self.app = app
        self.snapshots = OrderedDict()
        self.session = Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        self.session.headers.update({'Accept': 'application/json'})
        self.snapshot_folder = public_folder.joinpath('Snapshots')
        self.snapshot_folder.mkdir(exist_ok=True)
        self.snapshot_error_folder = public_folder.joinpath('Failed Snapshots')
        self.snapshot_error_folder.mkdir(exist_ok=True)
        app.add_url_rule('/snapshots/<uuid:_uuid>', view_func=self.view_phase, methods=['PATCH', 'GET'])

    def view_phase(self, _uuid: str):
        """
        Updates or creates a Snapshot.
        When the Snapshot is completed this will save it to a file and upload it to a DeviceHub.
        """
        if request.method == 'GET':
            try:
                snapshot_to_send = self.snapshots[_uuid].copy()
                self.remove_auxiliary_properties(snapshot_to_send)
                return jsonify(snapshot_to_send)
            except KeyError:
                raise NotFound()
        else:  # PATCH
            snapshot = request.get_json()
            snapshot['date'] = now()  # The client could have wrong timing so let's override with ours

            # We can receive two PATCH at the same time: from Workbench and DeviceHubClient
            # We merge the dictionaries to avoid data loss and to avoid forcing DeviceHubClient
            # to send all full snapshot
            snapshot = merge(self.snapshots.setdefault(_uuid, {}), snapshot)

            if snapshot['_phases'] == snapshot['_totalPhases'] and snapshot.get('_linked'):
                # todo devicehub won't allow us to link again a device that has been already uploaded
                # as it will have the same _uuid
                snapshot_to_send = copy(snapshot)
                self.remove_auxiliary_properties(snapshot_to_send)
                self.to_json_file(snapshot_to_send)
                snapshot['_saved'] = True
                try:
                    created_snapshot = self.to_devicehub(snapshot_to_send)
                    snapshot['_uploaded'] = created_snapshot['_id']
                except HTTPError as e:
                    self.to_json_file(snapshot_to_send, error=True)
                    snapshot['_error'] = json.loads(e.response.content.decode())
            return Response(status=204)

    @staticmethod
    def remove_auxiliary_properties(snapshot: dict):
        """Removes unwanted properties for DeviceHub from the snapshot. Mutates snapshot."""
        for attr in '_phases', '_totalPhases', '_linked', '_error', '_uploaded', '_saved':
            snapshot.pop(attr, None)

    def to_json_file(self, snapshot: dict, error=False):
        device = snapshot['device']
        un = 'Unknown'
        name = Naming.hid(device['manufacturer'] or un, device['serialNumber'] or un, device['model'] or un)
        folder = self.snapshot_folder if not error else self.snapshot_error_folder
        with folder.joinpath(name + '.json').open('w') as f:
            json.dump(snapshot, f, cls=DeviceHubJSONEncoder, indent=2, sort_keys=True)

    def to_devicehub(self, snapshot: dict):
        self.session.headers.update({'Authorization': self.app.auth})
        url = '{}/{}/events/devices/snapshot'.format(self.app.deviceHub, self.app.db)
        r = self.session.post(url, data=json.dumps(snapshot, cls=DeviceHubJSONEncoder))
        r.raise_for_status()
        return r.json()
