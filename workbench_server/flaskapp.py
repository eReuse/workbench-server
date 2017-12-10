from pathlib import Path
from typing import Type

import flask_cors
from ereuse_utils import DeviceHubJSONEncoder, ensure_utf8
from flask import Flask

from workbench_server.views.config import Config
from workbench_server.views.info import Info
from workbench_server.views.snapshots import Snapshots
from workbench_server.views.usbs import USBs


class WorkbenchServer(Flask):
    def __init__(self, import_name=__name__, static_path=None, static_url_path=None, static_folder='static',
                 template_folder='templates', instance_path=None, instance_relative_config=False, root_path=None,
                 folder=Path.home().joinpath('workbench'), info: Type[Info] = Info, config: Type[Config] = Config,
                 usbs: Type[USBs] = USBs, snapshots: Type[Snapshots] = Snapshots):
        ensure_utf8(self.__class__.__name__)
        super().__init__(import_name, static_path, static_url_path, static_folder, template_folder, instance_path,
                         instance_relative_config, root_path)
        self.json_encoder = DeviceHubJSONEncoder
        flask_cors.CORS(self,
                        origins='*',
                        allow_headers=['Content-Type', 'Authorization', 'Origin'],
                        expose_headers=['Authorization'],
                        max_age=21600)
        settings_folder = folder.joinpath('.settings')
        settings_folder.mkdir(parents=True, exist_ok=True)
        images_folder = folder.joinpath('images')
        images_folder.mkdir(exist_ok=True)

        self.configuration = config(self, settings_folder, images_folder)
        self.info = info(self)
        self.snapshots = snapshots(self, folder)
        self.usbs = usbs(self, settings_folder)
        self.auth = None
        self.deviceHub = None
        self.db = None
