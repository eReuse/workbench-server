from os import path
from shutil import copyfile

from workbench_server.web_service.flaskapp import WorkbenchWebService

original_config_ini = path.join(path.abspath(path.dirname(__file__)), 'workbench_server', 'tests',
                                'fixtures', 'config.ini')
tmp_config_ini = path.join('/tmp', 'workbench_server_run_config.ini')
copyfile(original_config_ini, tmp_config_ini)
app = WorkbenchWebService(__name__, config_ini=tmp_config_ini, json_path='~/Documents/json')
app.run('0.0.0.0', 8091, debug=True)
