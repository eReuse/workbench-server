from os import path, remove
from shutil import copyfile

from workbench_server.tests import TestBase
from workbench_server.web_service.flaskapp import WorkbenchWebService


class TestWebService(TestBase):
    def setUp(self):
        super().setUp()
        # As tests write in the config file we use a temporal one
        original_config_ini = path.join(path.abspath(path.dirname(path.dirname(__file__))), 'fixtures', 'config.ini')
        tmp_config_ini = path.join('/tmp', 'workbench_server_test_config.ini')
        copyfile(original_config_ini, tmp_config_ini)
        self.app = WorkbenchWebService(__name__, config_ini=tmp_config_ini, first_db=self.FIRST_DB)
        self.app.testing = True
        self.client = self.app.test_client()

    def tearDown(self):
        super().tearDown()
        remove(self.app.configuration.config_ini)