from workbench_server.tests import TestBase
from workbench_server.worker import Worker


class TestWorker(TestBase):
    def setUp(self):
        """Instantiate worker and clean databases."""
        super().setUp()
        # Note that we don't touch production dbs
        self.worker = Worker(host='localhost', json_path=self.fixtures, first_db=10)
        self.worker.device_hub['host'] = 'http://foo.bar'
        # Clean redis databases
        for db in self.worker.dbs:
            keys = db.keys()
            if keys:
                db.delete(*keys)
