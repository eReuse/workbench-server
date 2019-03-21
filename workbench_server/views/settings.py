from boltons import strutils
from flask import Response, current_app, jsonify, request

from workbench_server import flaskapp
from workbench_server.settings import WorkbenchSettings


class SettingsView:
    def __init__(self, app: 'flaskapp.WorkbenchServer') -> None:
        app.add_url_rule('/settings/', view_func=self.view, methods={'GET', 'POST'})
        app.add_url_rule('/settings/images/', view_func=self.view_images, methods={'GET'})

    def view(self):
        if request.method == 'GET':
            return jsonify(WorkbenchSettings.read())
        else:  # POST
            settings = WorkbenchSettings(**request.get_json())
            settings.write()
            return Response(status=204)

    def view_images(self):
        return jsonify(list(self.images()))

    def images(self):
        """Returns the images in images_path"""
        return (
            {
                'name': '{} – {}'.format(p.stem, strutils.bytes2human(p.stat().st_size)),
                'value': p.name
            }
            for p in current_app.dir.images.iterdir() if p.suffix == '.fsa'
        )
