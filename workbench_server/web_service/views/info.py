from collections import OrderedDict
from contextlib import suppress

from flask import json, jsonify


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
        # usbs
        usbs = []
        keys = self.app.dbs.usb.keys()
        if keys:
            for key, value in zip(keys, self.app.dbs.usb.mget(keys)):
                usb = json.loads(value.decode())
                usb['_uuid'] = key.decode()
                usbs.append(usb)
        response = {
            'devices': [{'key': k, 'val': v} for k, v in devices.items()],
            'usbs': usbs
        }
        with suppress(OSError):  # If no Internet
            response['ip'] = self.local_ip()
        return jsonify(response)

    @staticmethod
    def local_ip():
        """Gets the local IP of the interface that has access to the Internet."""
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
