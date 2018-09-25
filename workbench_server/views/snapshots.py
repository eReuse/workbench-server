import json
from collections import defaultdict, deque
from json import JSONDecodeError
from multiprocessing import Queue
from pathlib import Path
from sys import stderr
from threading import Thread
from time import sleep
from typing import List
from uuid import UUID

import requests
from ereuse_utils import session
from ereuse_utils.naming import Naming
from flask import Response, jsonify, request
from requests import HTTPError, Timeout
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
        self.snapshots = defaultdict(Snapshot)  # type: Snapshot
        output = Queue()
        Thread(target=self.from_submitter, args=(output,), daemon=True).start()
        self.submitter = DeviceHubSubmitter(public_folder, output)
        self.submitter.start()
        self.attempts = 0
        """
        Failed attempts to connect to DeviceHub due a connection error
        (ex. no WiFi)
        """
        app.add_url_rule('/snapshots/<uuid:_uuid>',
                         view_func=self.view_phase,
                         methods={'PATCH', 'GET'})

    def view_phase(self, _uuid: UUID):
        """
        Updates or creates a Snapshot.
        When the Snapshot is completed this will save it to a file
        and upload it to a DeviceHub.
        """
        if request.method == 'GET':
            try:
                return jsonify(self.snapshots[_uuid])
            except KeyError:
                raise NotFound()
        elif request.method == 'PATCH':
            s = request.get_json()
            snapshot = self.snapshots[_uuid]
            snapshot.update(s)
            if snapshot.closed(self.app.configuration.link):
                self.submitter.enqueue(snapshot, self.app.auth, self.app.device_hub, self.app.db)
        # Submit to Devicehub

        return Response(status=204)

    def get_snapshots(self) -> list:
        try:
            # We don't care for race conditions
            return list(self.snapshots.values())
        except RuntimeError:
            # A new snapshot was added while iterating
            # This happens only very rarely. Just try again
            return self.get_snapshots()

    def from_submitter(self, receiver_queue: Queue):
        while True:
            self.attempts, snapshot = receiver_queue.get()
            if snapshot:
                self.snapshots[UUID(snapshot['uuid'])] = snapshot


class DeviceHubSubmitter(Thread):
    def __init__(self, public_folder: Path, output: Queue):
        self.snapshot_folder = public_folder.joinpath('Snapshots')
        self.snapshot_folder.mkdir(exist_ok=True)
        self.snapshot_error_folder = public_folder.joinpath('Failed Snapshots')
        self.snapshot_error_folder.mkdir(exist_ok=True)
        self.server = session.Session()
        self.server.headers.update({'Content-Type': 'application/json'})
        self.server.headers.update({'Accept': 'application/json'})
        self.input = Queue()
        self.output = output
        super().__init__(daemon=True)

    def enqueue(self, snapshot: 'Snapshot', auth, device_hub, db):
        self.input.put((snapshot, auth, device_hub, db))

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
            snapshot, auth, device_hub, db = self.input.get()
            snapshots.append(snapshot)
            if auth:
                while snapshots:
                    snapshot = snapshots.popleft()
                    self._to_devicehub(snapshot, auth, device_hub, db, attempts=0)

    def _to_devicehub(self, snapshot: 'Snapshot', auth, device_hub, db, attempts=0):
        id = snapshot['uuid']
        # Snapshot without private keys
        snapshot_to_send = snapshot.dump_devicehub()

        self.server.headers.update({'Authorization': auth})
        url = '{}/{}/snapshot'.format(device_hub, db)
        try:
            r = self.server.post(url, json=snapshot_to_send)
        except (requests.ConnectionError, Timeout):
            print('Connection error for Snapshot {} & URL {}. Retrying in 4s.'.format(id, url))
            sleep(4)
            self.output.put((attempts, None))
            self._to_devicehub(snapshot, auth, device_hub, db, attempts + 1)  # Try again
        except HTTPError as e:
            t = 'HTTPError for Snapshot {}, ID {} and url {}:\n{}' \
                .format(id, snapshot['device'].get('_id', '(not linked)'), url, e)
            print(t, file=stderr)
            snapshot.save_file(self.snapshot_error_folder)
            error = e.response.content.decode()
            try:
                snapshot['_error'] = json.loads(error)
            except JSONDecodeError:
                snapshot['_error'] = error
            snapshot['_saved'] = True
            self.output.put((0, snapshot))
        else:
            print('Uploaded Snapshot {}, ID {} to url {}'
                  .format(id, snapshot['device'].get('_id', '(not linked)'), url))
            snapshot.save_file(self.snapshot_folder)
            snapshot['_uploaded'] = r.json()['_id']
            snapshot['_saved'] = True
            self.output.put((0, snapshot))


class Snapshot(dict):
    def __init__(self) -> None:
        super().__init__()
        self['_error'] = self['_uploaded'] = self['_saved'] = None

    def update(self, __m, **kwargs) -> None:
        super().update(__m, **kwargs)
        assert self['uuid']
        assert self['device']
        assert '_phase' in self
        assert 'expectedEvents' in self

    def closed(self, wait_for_link: bool):
        """Is the Snapshot finished?"""
        expected = self['expectedEvents']  # type: List
        actual = self['_phase']
        linked = self.get('tags', None)
        return (not expected or actual == expected[-1]) and (linked or not wait_for_link)

    def dump_devicehub(self) -> dict:
        """Creates a suitable dict for Devicehub."""
        return {k: v for k, v in self.items() if k[0] != '_'}

    @property
    def hid(self) -> str:
        un = 'Unknown'
        return Naming.hid(self['device'].get('manufacturer', un),
                          self['device'].get('serialNumber', un),
                          self['device'].get('model', un))

    def save_file(self, directory: Path):
        """Saves the Snapshot to a file."""
        s = self.dump_devicehub()
        with directory.joinpath(self.hid + '.json').open('w') as f:
            json.dump(s, f, indent=2, sort_keys=True)
