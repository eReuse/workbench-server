from contextlib import suppress
from typing import Type

import ereuse_utils
from flask import jsonify, request

from workbench_server import flaskapp
from workbench_server.mobile.models import SnapshotMobile
from workbench_server.models import Snapshot, SnapshotComputer
from workbench_server.settings import DevicehubConnection


class Info:
    def __init__(self, app: 'flaskapp.WorkbenchServer') -> None:
        self.app = app
        app.add_url_rule('/info/computer/', view_func=self.view_info_computer, methods=['GET'])
        app.add_url_rule('/info/mobile/', view_func=self.view_info_mobile, methods=['GET'])

    def view_info_computer(self):
        return self.info(SnapshotComputer)

    def view_info_mobile(self):
        return self.info(SnapshotMobile)

    def info(self, cls: Type[Snapshot]):
        if 'devicehub' in request.args:
            conn = DevicehubConnection(**request.args.to_dict())
            conn.write()

        response = {
            # We need to send snapshots as a list
            # so Javascript can keep the order
            'snapshots': list(cls.all_client()),
            'usbs': self.app.usbs.get_usbs()
        }
        with suppress(OSError):  # If no Internet
            response['ip'] = ereuse_utils.local_ip()
        return jsonify(response)
