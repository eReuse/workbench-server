import json
from collections import defaultdict, deque
from itertools import chain
from json import JSONDecodeError
from logging import Logger
from multiprocessing import Queue
from pathlib import Path
from threading import Thread
from time import sleep
from typing import Dict
from uuid import UUID

import deepmerge
import more_itertools
import requests
from boltons import urlutils
from ereuse_utils import session
from ereuse_utils.naming import Naming
from flask import Response, jsonify, request
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
        self.snapshots = defaultdict(Snapshot)  # type: Dict[UUID, Snapshot]
        self.unfinished_folder = public_folder / 'Unfinished Snapshots'
        self.unfinished_folder.mkdir(exist_ok=True)
        self.submitter = DeviceHubSubmitter(self.snapshots,
                                            public_folder,
                                            self.unfinished_folder,
                                            app.logger)
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
        """Updates or creates a Snapshot.

        When the Snapshot is completed this will save it to a file
        and upload it to a DeviceHub.
        """
        if request.method == 'GET':
            try:
                return jsonify(self.snapshots[_uuid])
            except KeyError:
                raise NotFound()
        elif request.method == 'PATCH':
            self.app.logger.debug('PATCH snapshot %s: %s', _uuid, request.data)
            # Update internal snapshot
            s = request.get_json()
            snapshot = self.snapshots[_uuid]
            snapshot.merge(s, self.app.configuration.link)
            snapshot.save_file(self.unfinished_folder)
            # Upload to Devicehub if ready
            if snapshot.ready_to_upload(self.app.configuration.link):
                self.app.logger.debug('Enqueued snapshot %s: %s', _uuid, request.data)
                self.submitter.enqueue(_uuid, self.app.auth, self.app.devicehub)
            else:
                self.app.logger.debug('Snapshot %s unready to upload.', _uuid)
        return Response(status=204)

    def get_snapshots(self) -> list:
        try:
            # We don't care for race conditions
            return list(self.snapshots.values())
        except RuntimeError:
            # A new snapshot was added while iterating
            # This happens only very rarely. Just try again
            return self.get_snapshots()


class DeviceHubSubmitter(Thread):
    def __init__(self, snapshots, public_folder: Path, unfinished_folder: Path, logger: Logger):
        self.logger = logger
        self.snapshots = snapshots
        self.snapshot_folder = public_folder / 'Snapshots'
        self.snapshot_folder.mkdir(exist_ok=True)
        self.snapshot_error_folder = public_folder / 'Failed Snapshots'
        self.snapshot_error_folder.mkdir(exist_ok=True)
        self.unfinished_folder = unfinished_folder
        self.server = session.Session()
        self.server.headers.update({'Content-Type': 'application/json'})
        self.server.headers.update({'Accept': 'application/json'})
        self.input = Queue()
        super().__init__(daemon=True)

    def enqueue(self, uuid, auth, devicehub):
        self.input.put((uuid, auth, devicehub))

    def run(self):
        """
        A separate process that uploads to DeviceHub.
        If there is a connection error it will try to upload again
        """
        snapshots_id = deque()
        """
        A queue of snapshots to submit.
        
        We keep accumulating snapshots until we have proper
        authentication to upload them to a DeviceHub.
        """
        while True:
            uuid, auth, devicehub = self.input.get()
            snapshots_id.append(uuid)
            if auth:
                while snapshots_id:
                    snapshot_id = snapshots_id.popleft()
                    self._to_devicehub(snapshot_id, auth, devicehub, attempts=0)

    def _to_devicehub(self, id: UUID, auth: str, devicehub: urlutils.URL, attempts=0):
        snapshot = self.snapshots[id]
        # Snapshot without private keys
        snapshot_to_send = snapshot.dump_devicehub()

        self.server.headers.update({'Authorization': auth})
        url = devicehub.to_text() + 'snapshots/'
        try:
            r = self.server.post(url, json=snapshot_to_send)
        except (requests.ConnectionError, requests.Timeout):
            self.logger.info('ConnectionError for %s to %s', id, url)
            sleep(10)
            self._to_devicehub(snapshot, auth, devicehub, attempts + 1)  # Try again
        except requests.HTTPError as e:
            name = snapshot.save_file(self.snapshot_error_folder)
            error = e.response.content.decode()
            try:
                snapshot['_error'] = json.loads(error)
            except JSONDecodeError:
                snapshot['_error'] = error
            snapshot['_saved'] = True

            self.logger.warning(
                'HTTPError for Snapshot %s, to %s. File saved as %s. Error %s %s:',
                id, url, name, e, snapshot['_error'])
        else:
            self.logger.info('Submitted Snapshot %s, %s', id, url)
            snapshot.save_file(self.snapshot_folder)
            snapshot['_uploaded'] = r.json()['id']
            snapshot['_saved'] = True
        snapshot.delete_file(self.unfinished_folder)
        snapshot.update_actual_phase(None)  # We don't care about link anymore


class Snapshot(dict):
    # Note that snapshot requires device.S/N, device.manufacturer
    # and device.model to be present, with a value or None
    MERGER = deepmerge.Merger(
        type_strategies=(
            (
                list,
                [
                    lambda _, __, orig, new: list(
                        more_itertools.unique_everseen(
                            chain(new, orig),
                            key=lambda x: x['id' if 'id' in x else 'type']
                        )
                    )
                ]
            ),
            (
                dict,
                ['merge']
            )
        ),
        fallback_strategies=['override'],
        type_conflict_strategies=['override']
    )
    """Dict merger that uses a list merge strategy 
    where it only returns unique values, 
    chosen by their 'type' key or the whole value by default."""

    def __init__(self) -> None:
        super().__init__()
        self['device'] = {
            'events': []
        }
        self['_error'] = self['_uploaded'] = self['_saved'] = None
        self['_linked'] = False
        """Is the device linked? i.e. has the user set a tag?"""

    def merge(self, new, wait_for_link=False) -> None:
        device = self.MERGER.merge(self['device'], new['device'])
        self.update(new)
        self['device'] = device
        self.update_actual_phase(wait_for_link)
        self['_linked'] = bool(self['device'].get('tags', None))
        assert self['uuid']
        assert self['device']
        assert '_phase' in self
        assert 'expectedEvents' in self

    def ready_to_upload(self, wait_for_link: bool):
        """Is the Snapshot finished?"""
        return self['closed'] and (self['_linked'] or not wait_for_link)

    def dump_devicehub(self) -> dict:
        """Creates a suitable dict for Devicehub."""
        return {k: v for k, v in self.items() if k[0] != '_'}

    def update_actual_phase(self, wait_for_link):
        """The phase that the Workbench is going through.

        This is the phase we received (which was the one that just
        finished) + 1.
        """
        self['_actualPhase'] = self._actual_phase(wait_for_link)

    def _actual_phase(self, wait_for_link):
        phase = self['_phase']
        if self['_error']:
            return 'Error'
        elif self['_uploaded']:
            return 'Uploaded'
        elif self.ready_to_upload(wait_for_link):
            return 'Uploading'
        elif self['closed'] and wait_for_link:
            return 'Link'
        elif phase:
            expected = self['expectedEvents']
            return expected[expected.index(phase) + 1]
        else:  # We received the info (1st phase)
            return self['expectedEvents'][0]

    @property
    def hid(self) -> str:
        un = 'Unknown'
        pc = self['device']
        return Naming.hid(pc['type'],
                          pc['model'] or un,
                          pc['manufacturer'] or un,
                          pc['serialNumber'] or un)

    def save_file(self, directory: Path) -> str:
        """Saves the Snapshot to a file. Returns the file name."""
        s = self.dump_devicehub()
        with directory.joinpath(self.hid + '.json').open('w') as f:
            json.dump(s, f, indent=2, sort_keys=True)
            return f.name

    def delete_file(self, directory: Path):
        directory.joinpath(self.hid + '.json').unlink()
