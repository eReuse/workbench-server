import json
import os
from unittest import TestCase

from workbench_server.worker.worker import Worker


class TestBase(TestCase):
    def setUp(self):
        """Instantiates the Worker, cleans the db and sets attributes."""
        self.fixtures = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'fixtures')
        # Note that we don't touch production dbs
        self.worker = Worker(host='localhost', json_path=self.fixtures, first_db=10)
        self.worker.device_hub['host'] = 'http://foo.bar'
        # Clean redis databases
        for db in self.worker.dbs:
            keys = db.keys()
            if keys:
                db.delete(*keys)
        super().setUp()

    def json(self, filename: str) -> dict:
        """
        Returns a JSON fixture as a dict. JSON must be inside fixtures folder.
        :param filename: The name of the json fixture without the extension.
        """
        with open(os.path.abspath(os.path.join(self.fixtures, filename + '.json'))) as file:
            return json.load(file)
