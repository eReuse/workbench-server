import json
import os
import pathlib
import time
from multiprocessing import Process
from pathlib import Path
from types import SimpleNamespace

import click
import ereuse_utils
import flask_cors
import requests
from boltons import urlutils
from ereuse_utils import cli, ensure_utf8
from ereuse_utils.test import Client
from flask import Flask

from workbench_server import manager
from workbench_server.db import db
from workbench_server.mobile import mobile
from workbench_server.views.info import Info
from workbench_server.views.settings import SettingsView
from workbench_server.views.snapshots import Snapshots
from workbench_server.views.usbs import USBs


class WorkbenchServer(Flask):
    """
    Server for Workbench. WorkbenchServer exposes a REST API where
    clients like Workbench and DeviceHub can interact to augment
    snapshotting computers.

    When Workbench is started with ``--server {url}`` it connects
    to an instance of this WorkbenchServer and keeps updating it
    with information about the computer and the snapshot process,
    finalizing with sending the full snapshot.

    WorkbenchServer complements Workbench by allowing the user,
    through a *DeviceHubClient*, introduce information that Workbench
    cannot take, like identifiers from stuck tags or visual and
    functional grades.

    WorkbenchServer allows you name USB pen-drives and auto-uploads
    snapshots to DeviceHub.
    """
    test_client_class = Client
    json_encoder = ereuse_utils.JSONEncoder
    DATABASE_URI = 'postgresql://dhub:ereuse@localhost/ws'

    def __init__(self,
                 import_name=__name__,
                 static_url_path=None,
                 static_folder='static',
                 static_host=None,
                 host_matching=False,
                 subdomain_matching=False,
                 template_folder='templates',
                 instance_path=None,
                 instance_relative_config=False,
                 root_path=None,
                 folder=Path.home() / 'workbench'):
        """Instantiates a WorkbenchServer.

       See params from base class Flask. New ones are:
       :param folder: The Path of the main folder for WorkbenchServer.
       WorkbenchServer will create configurations and read images from
       there. By defualt, ~/workbench
       :param info: Info class. Replace this to extend functionality.
       :param config: Config class. Replace this to extend func.
       :param usbs: USB class. Replace this to extend functionality.
       :param snapshots: Snapshots class. Replace this to extend func.
       """
        ensure_utf8(self.__class__.__name__)
        self.dir = SimpleNamespace()
        self.dir.main = folder
        self.dir.settings = folder / '.settings'
        self.dir.settings.mkdir(parents=True, exist_ok=True)
        self.dir.images = folder / 'images'
        self.dir.images.mkdir(parents=True, exist_ok=True)
        self.dir.snapshots = folder / 'snapshots'
        self.dir.snapshots.mkdir(parents=True, exist_ok=True)
        self.dir.failed_snapshots = folder / 'failed snapshots'
        self.dir.failed_snapshots.mkdir(parents=True, exist_ok=True)
        super().__init__(import_name, static_url_path, static_folder, static_host, host_matching,
                         subdomain_matching, template_folder, instance_path,
                         instance_relative_config, root_path)

        self.config['SQLALCHEMY_DATABASE_URI'] = self.DATABASE_URI
        self.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        db.init_app(self)

        # self.json_encoder = JSONEncoder
        flask_cors.CORS(self,
                        origins='*',
                        allow_headers=['Content-Type', 'Authorization', 'Origin'],
                        expose_headers=['Authorization'],
                        max_age=21600)

        self.settings_view = SettingsView(self)
        self.info = Info(self)
        self.snapshots = Snapshots(self, folder)
        self.usbs = USBs(self)
        self.cli.command('phase')(self.phase)
        self.cli.command('usb')(self.usb)
        self.cli.command('get-snapshots')(self.get_snapshots)
        self.cli.command('init-db')(self.init_db)
        self.manager = None
        self.mobile = None
        self.logger.info('Workbench Server initialized: %s', self)

    def init_manager(self):
        self.manager = Process(target=manager.main,
                               args=[self.dir.main],
                               name='wb-manager',
                               daemon=True)
        self.manager.start()

    def init_mobile(self):
        self.mobile = Process(target=mobile.main,
                              args=[self.dir.main],
                              name='wb-mobile',
                              daemon=True)
        self.mobile.start()

    @click.argument('phase')
    @click.option('--url', '-u',
                  type=cli.URL(scheme=True, host=True),
                  default=urlutils.URL('http://localhost:8091/'),
                  help='The URL where to make the petition to.')
    def phase(self, phase: str, url: urlutils.URL):
        """Performs a dummy PATCH to /snapshots emulating one device
        being processed.

        Pass-in PHASE to set which phase you want to submit.
        Options are (in natural order):

        1. info
        2. benchmark
        3. stress
        4. smart
        5. close

        i.e. flask phase benchmark will PATCH benchmark.
        """
        dir = pathlib.Path(__file__).parent / 'phases'
        base = 'http://localhost:8091/snapshots/{}'
        if phase == 'info':
            s = json.loads(dir.joinpath('1.json').read_text())
            url = base.format(s['uuid'])
            requests.post(url, json=s).raise_for_status()
        if phase == 'benchmark':
            b = json.loads(dir.joinpath('4.json').read_text())
            requests.post(base.format(b['uuid']) + '/device/action', json=b).raise_for_status()
        if phase == 'stress':
            s = json.loads(dir.joinpath('6.json').read_text())
            requests.post(base.format(s['uuid']) + '/device/action', json=s).raise_for_status()
        if phase == 'smart':
            s = json.loads(dir.joinpath('12.json').read_text())
            requests.post(base.format(s['uuid']) + '/device/action', json=s).raise_for_status()
        if phase == 'close':
            s = json.loads(dir.joinpath('14.json').read_text())
            requests.patch(base.format(s['uuid']), json=s).raise_for_status()

    @click.option('--seconds', '-s',
                  type=int,
                  default=16,
                  help='The amount of seconds to keep the USB plugged-in.')
    @click.option('--url', '-u',
                  type=cli.URL(scheme=True, host=True),
                  default=urlutils.URL('http://localhost:8091/'),
                  help='The URL where to make the petition to.')
    def usb(self, url, seconds):
        """Plugs an USB for the device being processed in Phase.

        This keeps the USB plugged-in for X seconds.

        Execute at least one phase before executing this.
        """
        with (pathlib.Path(__file__).parent / 'phases' / 'usb.json').open() as f:
            s = json.load(f)
            url = url.navigate('/usbs/kingston-0014780ee3fbf090d52f1286-dt_101_g2').to_text()
            for _ in range(seconds // 4):
                requests.post(url, json=s).raise_for_status()
                time.sleep(4)

    @click.option('--url', '-u',
                  type=cli.URL(scheme=True, host=True),
                  default=urlutils.URL('http://localhost:8091/'),
                  help='The URL where to make the petition to.')
    @click.option('--dir', '-d',
                  type=cli.Path(dir_okay=True, file_okay=False),
                  help='The directory where to save the snapshots. '
                       'By default the current dir.',
                  default=pathlib.Path(os.getcwd()))
    def get_snapshots(self, url: urlutils.URL, dir: pathlib.Path):
        """Saves all the snapshots that are in Workbench Server's
        memory as JSON files."""
        info = requests.get(url.navigate('/info/').to_text()).json()
        for snapshot in info['snapshots']:
            _uuid = snapshot['_uuid']
            endpoint = url.navigate('/snapshots/{}'.format(_uuid)).to_text()
            with dir.joinpath('{}.json'.format(_uuid)).open('w') as f:
                json.dump(requests.get(endpoint).json(), f)

    def init_db(self):
        db.drop_all()
        db.create_all()
        print(cli.done())
