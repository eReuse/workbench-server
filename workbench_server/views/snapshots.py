import json
from collections import defaultdict, deque
from json import JSONDecodeError
from multiprocessing import Process, Queue
from pathlib import Path
from sys import stderr
from threading import Thread
from time import sleep
from uuid import UUID

import requests
from ereuse_utils import DeviceHubJSONEncoder, now
from ereuse_utils.naming import Naming
from flask import Response, jsonify, request
from pydash import merge
from requests import HTTPError, Session, Timeout
from werkzeug.exceptions import NotFound

from workbench_server import flaskapp


class Snapshots:
    """
    Saves incoming snapshots,
    storing them to a file and uploading them to a DeviceHub when they
    are completed (all phases done and linked).
    """

    def __init__(self, app: 'flaskapp.WorkbenchServer', public_folder: Path) -> None:
        self.app = app
        self.snapshots = defaultdict(dict)
        self.sender_queue = Queue()
        self.receiver_queue = Queue()
        self.snapshot_folder = public_folder.joinpath('Snapshots')
        self.snapshot_folder.mkdir(exist_ok=True)
        self.submitter = DeviceHubSubmitter(public_folder, self.sender_queue, self.receiver_queue)
        self.submitter.start()
        Thread(target=self.update_from_submitter, args=(self.receiver_queue,), daemon=True).start()
        self.attempts = 0
        """
        Failed attempts to connect to DeviceHub due a connection error
        (ex. no WiFi)
        """
        app.add_url_rule('/snapshots/<uuid:_uuid>', view_func=self.view_phase,
                         methods={'PATCH', 'GET'})

    def view_phase(self, _uuid: UUID):
        """
        Updates or creates a Snapshot.
        When the Snapshot is completed this will save it to a file
        and upload it to a DeviceHub.
        """
        _uuid = str(_uuid)
        if request.method == 'GET':
            try:
                snapshot_to_send = self.snapshots[_uuid].copy()
                remove_auxiliary_properties(snapshot_to_send)
                return jsonify(snapshot_to_send)
            except KeyError:
                raise NotFound()
        else:  # PATCH
            snapshot = request.get_json()
            # Client could have wrong timing so we override it with ours
            snapshot['date'] = now()

            # We can receive two PATCH at the same time:
            # from Workbench and DeviceHubClient
            # We merge the dictionaries to avoid data loss
            # and to avoid forcing DeviceHubClient
            # to send all full snapshot
            snapshot = merge(self.snapshots[_uuid], snapshot)
            # We create control variables under
            # lock so modifying them later does not change dict size
            snapshot['_error'] = snapshot['_uploaded'] = snapshot['_saved'] = None

            # Note that _phases might not exist if we link
            # before we get the snapshot from the first phase
            if snapshot.get('_phases') and snapshot['_phases'] == snapshot['_totalPhases'] \
                    and (snapshot.get('_linked') or not self.app.configuration.link):
                # todo devicehub won't allow us to link again a device
                # that has been already uploaded as it will have the
                # same _uuid
                self.sender_queue.put((snapshot, self.app.auth, self.app.device_hub, self.app.db))
                # Save copy of snapshot
                snapshot_to_send = snapshot.copy()
                remove_auxiliary_properties(snapshot_to_send)
                DeviceHubSubmitter.to_json_file(snapshot_to_send, self.snapshot_folder)

            return Response(status=204)

    def get_snapshots(self) -> list:
        try:
            # We don't care for race conditions
            return list(self.snapshots.values())
        except RuntimeError:
            print('runtimeError with Snapshots')
            # A new snapshot was added while iterating
            # This happens only very rarely. Just try again
            return self.get_snapshots()

    def update_from_submitter(self, receiver_queue: Queue):
        while True:
            self.attempts, snapshot = receiver_queue.get()
            if snapshot:
                self.snapshots[str(snapshot['_uuid'])] = snapshot


class DeviceHubSubmitter(Process):
    def __init__(self, public_folder: Path, input_queue: Queue, output_queue: Queue):
        self.snapshot_folder = public_folder.joinpath('Snapshots')
        self.snapshot_error_folder = public_folder.joinpath('Failed Snapshots')
        self.snapshot_error_folder.mkdir(exist_ok=True)
        self.server = Session()
        self.server.headers.update({'Content-Type': 'application/json'})
        self.server.headers.update({'Accept': 'application/json'})
        self.input_queue = input_queue
        self.output_queue = output_queue
        super().__init__(daemon=True)

    def run(self):
        """
        A separate process that uploads to DeviceHub.
        If there is a connection error it will try to upload again
        """
        snapshots = deque()
        """
        A queue of snapshots to submit.
        
        We keep accumulating snapshots until we have proper
        authentication to upload them to a DeviceHub.
        """
        while True:
            _uuid, auth, device_hub, db = self.input_queue.get()
            snapshots.append(_uuid)
            if auth:
                while snapshots:
                    snapshot = snapshots.popleft()
                    self._to_devicehub(snapshot, auth, device_hub, db, attempts=0)

    def _to_devicehub(self, snapshot: dict, auth, device_hub, db, attempts=0):
        _uuid = snapshot['_uuid']
        snapshot_to_send = snapshot.copy()
        remove_auxiliary_properties(snapshot_to_send)

        self.server.headers.update({'Authorization': auth})
        url = '{}/{}/events/devices/snapshot'.format(device_hub, db)
        try:
            r = self.server.post(url, data=json.dumps(snapshot_to_send, cls=DeviceHubJSONEncoder))
            r.raise_for_status()
        except (requests.ConnectionError, Timeout):
            print('Connection error for Snapshot {} & URL {}. Retrying in 4s.'.format(_uuid, url))
            sleep(4)
            self.output_queue.put((attempts, None))
            self._to_devicehub(snapshot, auth, device_hub, db, attempts + 1)  # Try again
        except HTTPError as e:
            t = 'HTTPError for Snapshot {}, ID {} and url {}:\n{}' \
                .format(_uuid, snapshot['device'].get('_id', '(not linked)'), url, e)
            print(t, file=stderr)
            self.to_json_file(snapshot_to_send, self.snapshot_error_folder)
            error = e.response.content.decode()
            try:
                snapshot['_error'] = json.loads(error)
            except JSONDecodeError:
                snapshot['_error'] = error
            snapshot['_saved'] = True
            self.output_queue.put((0, snapshot))
        else:
            print('Uploaded Snapshot {}, ID {} to url {}'
                  .format(_uuid, snapshot['device'].get('_id', '(not linked)'), url))
            self.to_json_file(snapshot_to_send, self.snapshot_folder)
            snapshot['_uploaded'] = r.json()['_id']
            snapshot['_saved'] = True
            self.output_queue.put((0, snapshot))

    @staticmethod
    def to_json_file(snapshot: dict, folder: Path):
        device = snapshot['device']
        un = 'Unknown'
        name = Naming.hid(device['manufacturer'] or un, device['serialNumber'] or un,
                          device['model'] or un)
        name = '{} {}'.format(name, snapshot['_uuid'])
        with folder.joinpath(name + '.json').open('w') as f:
            json.dump(snapshot, f, indent=2, sort_keys=True, cls=DeviceHubJSONEncoder)


def remove_auxiliary_properties(snapshot: dict):
    """
    Removes unwanted properties for DeviceHub from the snapshot.

    Mutates snapshot.
    """
    for attr in '_phases', '_totalPhases', '_linked', '_error', '_uploaded', '_saved':
        snapshot.pop(attr, None)
