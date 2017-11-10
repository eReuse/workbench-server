import flask_cors
from flask import Flask

from workbench_server.web_service.views.config import Config
from workbench_server.web_service.views.info import Info
from workbench_server.web_service.views.link import Link
from workbench_server.worker import Worker


class WorkbenchWebService(Flask):
    def __init__(self, import_name, static_path=None, static_url_path=None, static_folder='static',
                 template_folder='templates', instance_path=None, instance_relative_config=False, root_path=None,
                 config_ini='/srv/ereuse-data/config.ini', json_path='/srv/ereuse-data/inventory', config=Config,
                 info=Info, first_db: int = 1, link=Link, db_host='localhost'):
        super().__init__(import_name, static_path, static_url_path, static_folder, template_folder, instance_path,
                         instance_relative_config, root_path)
        flask_cors.CORS(self,
                        origins='*',
                        allow_headers=['Content-Type', 'Authorization', 'Origin'],
                        expose_headers=['Authorization'],
                        max_age=21600)
        self.dbs = Worker.instantiate_dbs(db_host, first_db)
        self.configuration = config(self, config_ini)
        self.link = link(self)
        self.info = info(self)
        self.json_path = json_path
