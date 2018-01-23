import json
from pathlib import Path

from flask import Response, jsonify, request

from workbench_server import flaskapp


class Config:
    def __init__(self, app: 'flaskapp.WorkbenchServer', settings_path: Path,
                 images_path: Path) -> None:
        self.config = settings_path.joinpath('config.json')
        self.link = True  # Please Keep default in sync with DeviceHubClient
        """
        Shortcut to the link config property. 
        'Wait for user to link computer without uploading them to
        DeviceHub'.
        """
        self.images_path = images_path
        app.add_url_rule('/config', view_func=self.view, methods={'GET', 'POST'})

    def view(self):
        if request.method == 'GET':
            try:
                with self.config.open() as f:
                    config = json.load(f)
            except FileNotFoundError:
                config = {}
            return jsonify(config)
        else:  # POST
            config = request.get_json()
            self.link = config['link']
            with self.config.open(mode='w') as f:
                json.dump(config, f)
            return Response(status=204)
