import logging
from datetime import datetime, timedelta
from json import JSONDecodeError
from time import sleep

import requests
from ereuse_utils.session import DevicehubClient, retry
from flask import json

from workbench_server.db import db
from workbench_server.log import log
from workbench_server.models import Phases, Snapshot
from workbench_server.settings import DevicehubConnection


class Manager:
    SLEEP = 20

    def __init__(self, app) -> None:
        from workbench_server.flaskapp import WorkbenchServer
        assert isinstance(app, WorkbenchServer)
        self.app = app
        self.failed = self.app.dir.main / 'Failed Snapshots'
        # Drop connections created by WS on the parent process
        with self.app.app_context():
            db.engine.dispose()
        logging.info('Manager initialized: %s', self)

    def run(self):
        while True:
            try:
                with self.app.app_context():
                    self.upload_snapshots()
            except Exception as e:
                logging.error('Unhandled error in Manager')
                logging.exception(e)
            # with self.app.app_context():
            #    self.clean_snapshots()
            sleep(self.SLEEP)

    def clean_snapshots(self):
        """Delete snapshots from the local database that have been
        uploaded and closed for more than one day.
        """
        # q = () & \
        #    (Snapshot.phase == Phases.Uploaded)
        x = (datetime.now() - timedelta(days=1))
        Snapshot.query.filter(Snapshot.closed < x).delete()
        db.session.commit()

    def upload_snapshots(self):
        conn = DevicehubConnection.read()
        if not conn:  # No devicehub yet set
            logging.debug('No devicehub yet set: %s', conn)
            return

        dh = retry(DevicehubClient(conn.devicehub, token=conn.token, inventory=conn.db))
        q = Snapshot.phase.in_((Phases.ReadyToUpload, Phases.ConnectionError))
        for snapshot in Snapshot.query.filter(q):  # type: Snapshot
            self._upload_one(dh, snapshot)

    def _upload_one(self, dh: DevicehubClient, snapshot: Snapshot):
        logging.debug('Going to upload snapshot %s to %s', snapshot, dh)
        try:
            new_snapshot, r = dh.post('events/', snapshot.data)
        except (requests.ConnectionError, requests.Timeout) as e:
            logging.warning('ConnectionError for %s to %s: %s', snapshot, dh, e)
        except requests.HTTPError as e:
            error = e.response.content.decode()
            path = snapshot.write(self.app.dir.failed_snapshots)
            try:
                snapshot.error = json.loads(error)
            except JSONDecodeError:
                snapshot.error = error
            snapshot.phase = Phases.HTTPError
            logging.error('HTTPError for Snapshot %s (saved as %s): %s', snapshot, path, error)
        except Exception as e:
            logging.exception(e)
            snapshot.phase = Phases.ConnectionError
        else:
            snapshot.data['id'] = new_snapshot['id']
            logging.info('Submitted Snapshot %s to %s', snapshot, dh)
            snapshot.phase = Phases.Uploaded
            snapshot.write()
        db.session.commit()


def main(folder):
    log(name='manager.log')
    from workbench_server.flaskapp import WorkbenchServer
    up = Manager(WorkbenchServer(folder=folder))
    up.run()
