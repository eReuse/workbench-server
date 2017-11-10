import json
import os
from unittest import TestCase


class TestBase(TestCase):
    def setUp(self):
        """Instantiates the Worker, cleans the db and sets attributes."""
        super().setUp()
        self.fixtures = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'fixtures')
        self.FIRST_DB = 10

    def json(self, filename: str) -> dict:
        """
        Returns a JSON fixture as a dict. JSON must be inside fixtures folder.
        :param filename: The name of the json fixture without the extension.
        """
        with open(os.path.abspath(os.path.join(self.fixtures, filename + '.json'))) as file:
            return json.load(file)
