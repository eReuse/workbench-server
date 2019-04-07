import logging
from pathlib import Path
from time import sleep

from workbench_server.db import db
from workbench_server.log import log
from workbench_server.mobile.models import NoDevice, SnapshotMobile


class WorkbenchMobile:
    SLEEP = 3

    def __init__(self, app) -> None:
        from workbench_server.flaskapp import WorkbenchServer
        assert isinstance(app, WorkbenchServer)
        self.app = app
        self.androids = app.dir.main / 'mobile'  # type: Path
        self.androids.mkdir(exist_ok=True)
        super().__init__()
        logging.info('Workbench Mobile initialized: %s', self)

    def run(self):
        while True:
            try:
                self._run()
            except Exception as e:
                logging.error('Unhandled exception in Workbench Mobile:')
                logging.exception(e)
                with self.app.app_context():
                    SnapshotMobile.query.delete()
                    db.session.commit()
                logging.info('Deleted all mobiles to clean exception.')
            sleep(self.SLEEP)

    def _run(self):
        with self.app.app_context():
            try:
                snapshot = SnapshotMobile.new()
            except NoDevice:
                logging.debug('No new mobile detected.')
            except Exception as e:
                logging.error('Unhandled error in WorkbenchAndroid:')
                logging.exception(e)
            else:
                db.session.add(snapshot)
                db.session.commit()
                logging.info('New snapshot mobile: %s', snapshot)
                try:
                    snapshot.run(self.androids)
                    db.session.add(snapshot)
                    db.session.commit()
                except Exception as e:
                    logging.error('Unhandled exception in run in Workbench Mobile:')
                    logging.exception(e)
                    with self.app.app_context():
                        db.session.delete(snapshot)
                        db.session.commit()
                    logging.info('Delete the Snapshot Mobile %s', snapshot)
                else:
                    logging.info('Snapshot mobile finished: %s', snapshot)


def main(folder):
    log(name='mobile.log')
    from workbench_server.flaskapp import WorkbenchServer
    android = WorkbenchMobile(WorkbenchServer(folder=folder))
    android.run()
