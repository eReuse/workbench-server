from contextlib import suppress
from os import mkdir

from workbench_server.tests import TestBase
from workbench_server.worker import Worker


class TestWorker(TestBase):
    def setUp(self):
        """Instantiate worker and clean databases."""
        super().setUp()
        # Note that we don't touch production dbs
        self.worker = Worker(host='localhost', json_path=self.JSON_PATH, first_db=self.FIRST_DB)
        self.worker.device_hub['host'] = 'http://foo.bar'
        self.setUp_dbs()

    def setUp_dbs(self):
        # Clean redis databases
        for db in self.worker.dbs:
            keys = db.keys()
            if keys:
                db.delete(*keys)
