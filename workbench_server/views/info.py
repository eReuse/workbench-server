from contextlib import suppress

from boltons import urlutils
from flask import jsonify, request

from workbench_server import flaskapp


class Info:
    def __init__(self, app: 'flaskapp.WorkbenchServer') -> None:
        self.app = app
        app.add_url_rule('/info/', view_func=self.view_info, methods=['GET'])

    def view_info(self):
        if 'device-hub' in request.args:
            self.app.devicehub = urlutils.URL(request.args['device-hub'])
            # Just avoid this for now
            if request.args.get('db', None):
                self.app.devicehub = self.app.devicehub.navigate(request.args.get('db') + '/')
            self.app.auth = request.headers['Authorization']

        response = {
            # We need to send snapshots as a list
            # so Javascript can keep the order
            'snapshots': self.app.snapshots.get_snapshots(),
            'usbs': self.app.usbs.get_usbs(),
            'attempts': self.app.snapshots.attempts
        }
        with suppress(OSError):  # If no Internet
            response['ip'] = self.local_ip()
        return jsonify(response)

    @staticmethod
    def local_ip():
        """
        Gets the local IP of the interface that
        has access to the Internet.
        """
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
