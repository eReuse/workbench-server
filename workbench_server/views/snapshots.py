import json
from collections import defaultdict
from copy import copy
from multiprocessing import Queue
from pathlib import Path
from threading import Thread
from time import sleep

import requests
from ereuse_utils import DeviceHubJSONEncoder, now
from ereuse_utils.naming import Naming
from flask import Response, jsonify, request
from prwlock import RWLock
from pydash import merge
from requests import HTTPError, Session, Timeout
from werkzeug.exceptions import NotFound

from workbench_server import flaskapp


class Snapshots:
    """
    Saves incoming snapshots, saving them to a file and uploading them to a DeviceHub when they
    are completed (all phases done and linked).
    """

    def __init__(self, app: 'flaskapp.WorkbenchServer', public_folder: Path) -> None:
        self.app = app
        self.snapshots = defaultdict(dict)
        self.snapshots_lock = RWLock()
        self.snapshot_folder = public_folder.joinpath('Snapshots')
        self.snapshot_folder.mkdir(exist_ok=True)
        self.snapshot_error_folder = public_folder.joinpath('Failed Snapshots')
        self.snapshot_error_folder.mkdir(exist_ok=True)

        self.sender_queue = Queue()
        self.sender = Thread(target=self.to_devicehub, args=(self.sender_queue,), daemon=True)
        self.sender.start()
        self.attempts = 0
        """Failed attempts to connect to DeviceHub due a connection error (ex. no WiFi)"""
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
            snapshot['date'] = now()  # The client could have wrong timing so let's override it with ours

            # We can receive two PATCH at the same time: from Workbench and DeviceHubClient
            # We merge the dictionaries to avoid data loss and to avoid forcing DeviceHubClient
            # to send all full snapshot
            with self.snapshots_lock.writer_lock():
                snapshot = merge(self.snapshots[_uuid], snapshot)
                # We create control variables under lock so modifying them later does not change dict size
                snapshot['_error'] = snapshot['_uploaded'] = snapshot['_saved'] = None

            # Note that _phases might not exist if we link before we get the snapshot from the first phase
            if snapshot.get('_phases') and snapshot['_phases'] == snapshot['_totalPhases'] and snapshot.get('_linked'):
                # todo devicehub won't allow us to link again a device that has been already uploaded
                # as it will have the same _uuid
                self.sender_queue.put((_uuid,))

            return Response(status=204)

    def get_snapshots(self) -> list:
        with self.snapshots_lock.reader_lock():
            return list(self.snapshots.values())

    @staticmethod
    def remove_auxiliary_properties(snapshot: dict):
        """Removes unwanted properties for DeviceHub from the snapshot. Mutates snapshot."""
        for attr in '_phases', '_totalPhases', '_linked', '_error', '_uploaded', '_saved':
            snapshot.pop(attr, None)

    @staticmethod
    def to_json_file(snapshot: dict, folder: Path):
        device = snapshot['device']
        un = 'Unknown'
        name = Naming.hid(device['manufacturer'] or un, device['serialNumber'] or un, device['model'] or un)
        with folder.joinpath(name + '.json').open('w') as f:
            json.dump(snapshot, f, indent=2, sort_keys=True, cls=DeviceHubJSONEncoder)

    def to_devicehub(self, queue: Queue):
        """
        A separate process that uploads to DeviceHub.
        If there is a connection error it will try to upload again
        """
        session = Session()
        session.headers.update({'Content-Type': 'application/json'})
        session.headers.update({'Accept': 'application/json'})
        while True:
            _uuid = queue.get()[0]
            self._to_devicehub(_uuid, session)

    def _to_devicehub(self, _uuid, session):
        snapshot = self.snapshots[_uuid]
        snapshot_to_send = copy(snapshot)
        self.remove_auxiliary_properties(snapshot_to_send)

        session.headers.update({'Authorization': self.app.auth})
        url = '{}/{}/events/devices/snapshot'.format(self.app.deviceHub, self.app.db)
        try:
            r = session.post(url, data=json.dumps(snapshot_to_send, cls=DeviceHubJSONEncoder))
            r.raise_for_status()
        except (requests.ConnectionError, Timeout):
            self.attempts += 1
            print('Connection error for Snapshot {} and URL {}. Retrying in 4s.'.format(_uuid, url))
            sleep(4)
            self._to_devicehub(_uuid, session)  # Try again
        except HTTPError as e:
            self.attempts = 0
            self.to_json_file(snapshot_to_send, self.snapshot_error_folder)
            snapshot['_error'] = json.loads(e.response.content.decode())
            snapshot['_saved'] = True
        else:
            self.attempts = 0
            self.to_json_file(snapshot_to_send, self.snapshot_folder)
            snapshot['_uploaded'] = r.json()['_id']
            snapshot['_saved'] = True
