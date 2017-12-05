from collections import OrderedDict
from contextlib import suppress

from flask import json, jsonify
from werkzeug.exceptions import NotFound


class Info:
    def __init__(self, app) -> None:
        self.app = app
        app.add_url_rule('/info', view_func=self.view_info, methods=['GET'])

    def view_info(self):
        # devices
        devices = OrderedDict()
        for db in self.app.dbs.redis, self.app.dbs.consolidated, self.app.dbs.uploaded, self.app.dbs.upload_errors:
            keys = db.keys('*')
            if keys:
                for key, device in zip(keys, db.mget(keys)):
                    devices[key.decode()] = json.loads(device.decode())

        def add_usb_name(usb):
            with suppress(NotFound):
                usb['name'] = self.app.usbs.get_named_usb(usb['serialNumber'])['name']
            return usb

        response = {
            'devices': [{'key': k, 'val': v} for k, v in devices.items()],
            'usbs': [add_usb_name(usb) for _, usb in self.app.usbs.client_plugged.items()],
            'names': self.app.usbs.get_all_named_usbs()
        }
        return jsonify(response)
