import glob
import json
import os
from contextlib import suppress
from unittest import TestCase

from shutil import rmtree


class TestBase(TestCase):
    def setUp(self):
        """Instantiates the Worker, cleans the db and sets attributes."""
        super().setUp()
        self.fixtures = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'fixtures')
        self.JSON_PATH = '/tmp/inventory'
        with suppress(FileNotFoundError):
            rmtree(self.JSON_PATH)
        os.mkdir(self.JSON_PATH)
        self.FIRST_DB = 10

    def json(self, filename: str) -> dict:
        """
        Returns a JSON fixture as a dict. JSON must be inside fixtures folder.
        :param filename: The name of the json fixture without the extension.
        """
        with open(os.path.abspath(os.path.join(self.fixtures, filename + '.json'))) as file:
            return json.load(file)

    def json_from_inventory(self):
        try:
            with open(glob.glob('{}/*.json'.format(self.JSON_PATH))[0]) as f:
                return json.load(f)
        except IndexError:
            raise AssertionError('No inventory JSON files')
