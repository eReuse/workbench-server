import json

from flask import Response, request

from workbench_server.worker import Worker


class Link:
    def __init__(self, app) -> None:
        self.app = app
        app.add_url_rule('/link', view_func=self.view_link, methods=['POST'])
        app.add_url_rule('/usbs/<_uuid>', view_func=self.remove_usb, methods=['DELETE'])

    def view_link(self):
        snapshot = request.get_json()
        self.link(snapshot)
        return Response(status=201)

    def remove_usb(self, _uuid):
        self.app.dbs.usb.delete(_uuid)
        return Response(status=200)

    def link(self, snapshot: dict):
        _uuid = snapshot['_uuid']
        aggregated_json = self.app.dbs.redis.get(_uuid)
        if aggregated_json is not None:
            aggregated_json = json.loads(aggregated_json.decode())

            if snapshot.get('gid', False):
                aggregated_json['gid'] = snapshot['gid']
            if snapshot.get('_id', False):
                aggregated_json['_id'] = snapshot['_id']

            aggregated_json['device']['type'] = snapshot['device_type']
            aggregated_json['condition'] = {
                'appearance': {'general': snapshot['visual_grade']},
                'functionality': {'general': snapshot['functional_grade']}
            }

            if snapshot.get('comment', ''):
                aggregated_json['comment'] = snapshot['comment']

            self.app.dbs.redis.set(_uuid, json.dumps(aggregated_json))

            if len(aggregated_json['times'].keys()) > 5:
                # We have passed by all phases (regardless if we had to perform them)
                Worker.consolidate_json(aggregated_json, self.app.dbs.redis, self.app.dbs.consolidated,
                                        self.app.json_path)
