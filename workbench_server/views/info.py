from contextlib import suppress

import ereuse_utils
from flask import jsonify, request

from workbench_server import flaskapp
from workbench_server.models import Snapshot
from workbench_server.settings import DevicehubConnection


class Info:
    def __init__(self, app: 'flaskapp.WorkbenchServer') -> None:
        self.app = app
        app.add_url_rule('/info/', view_func=self.view_info, methods=['GET'])

    def view_info(self):
        if 'devicehub' in request.args:
            conn = DevicehubConnection(**request.args.to_dict())
            conn.write()

        response = {
            # We need to send snapshots as a list
            # so Javascript can keep the order
            'snapshots': list(Snapshot.all()),
            'usbs': self.app.usbs.get_usbs()
        }
        with suppress(OSError):  # If no Internet
            response['ip'] = ereuse_utils.local_ip()
        return jsonify(response)
