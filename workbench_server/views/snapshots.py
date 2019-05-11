import uuid as uuid_mod
from logging import Logger
from pathlib import Path
from typing import Type

from flask import Response, jsonify, request

from workbench_server import flaskapp
from workbench_server.db import db
from workbench_server.mobile.models import SnapshotMobile
from workbench_server.models import Progress, Snapshot, SnapshotComputer


class Snapshots:
    """
    Saves incoming snapshots,
    storing them to a file and uploading them to a DeviceHub when they
    are completed (all phases done and linked).
    """

    def __init__(self, app: 'flaskapp.WorkbenchServer', public_folder: Path) -> None:
        self.dir = app.dir.main / 'Snapshots'
        self.logger = app.logger  # type: Logger
        url = '/snapshots/<uuid:uuid>'
        POST = {'POST'}
        app.add_url_rule(url, view_func=self.view_get, methods={'GET', 'POST', 'PATCH'})
        app.add_url_rule(url + '/progress/', view_func=self.view_progress, methods=POST)
        app.add_url_rule(url + '/device/action/', view_func=self.view_action, methods=POST)
        app.add_url_rule(url + '/components/<int:pos>/action/',
                         view_func=self.view_action,
                         methods=POST)
        app.add_url_rule(url + '/form/', view_func=self.view_form, methods=POST)
        app.add_url_rule('/snapshots/mobile/', view_func=self.view_all_mobile, methods={'DELETE'})
        app.add_url_rule('/snapshots/computer/', view_func=self.view_all_computer,
                         methods={'DELETE'})

    def view_all_mobile(self):
        return self.view_all(SnapshotMobile)

    def view_all_computer(self):
        return self.view_all(SnapshotComputer)

    def view_all(self, cls: Type[Snapshot]):
        assert request.method == 'DELETE'
        snapshots = tuple(cls.query.filter(cls.closed != None))
        for s in snapshots:
            db.session.delete(s)
        db.session.commit()
        self.logger.info('DELETE %s: %s', cls, snapshots)
        return Response(status=204)

    def view_get(self, uuid: uuid_mod.UUID):
        if request.method == 'GET':
            res = jsonify(SnapshotComputer.one(uuid))
        elif request.method == 'POST':
            self.logger.debug('POSTing a new snapshot %s', uuid)
            s = request.get_json()
            snapshot = SnapshotComputer(uuid=uuid, data=s)
            db.session.add(snapshot)
            db.session.commit()
            self.logger.info('Snapshot %s created.', snapshot)
            res = Response(status=204)
        else:  # PATCH
            self.logger.debug('PATCHing snapshot %s', uuid)
            s = request.get_json()
            snapshot = SnapshotComputer.one(uuid)
            snapshot.close(s)  # No more actions from workbench
            db.session.commit()
            self.logger.info('Snapshot closed %s', snapshot)
            res = Response(status=204)
        return res

    def view_action(self, uuid: uuid_mod.UUID, pos: int = None):
        action = request.get_json()
        snapshot = SnapshotComputer.one(uuid)
        snapshot.set_action(action, pos)
        snapshot.conditionally_set_phase_from_action(action['type'])
        db.session.commit()
        self.logger.info('Action for snapshot %s and pos %s: %s', snapshot, pos, action)
        return Response(status=204)

    def view_form(self, uuid: uuid_mod.UUID):
        form = request.get_json()
        snapshot = Snapshot.one(uuid)
        snapshot.from_form(form)
        db.session.commit()
        self.logger.debug('Form for snapshot %s: %s', snapshot, form)
        return Response(status=204)

    def view_progress(self, uuid: uuid_mod.UUID):
        p = request.get_json()
        progress = Progress.set(uuid=uuid, **p)
        db.session.add(progress)
        db.session.commit()
        self.logger.debug('Progress for snapshot %s: %s', uuid, p)
        return Response(status=204)
