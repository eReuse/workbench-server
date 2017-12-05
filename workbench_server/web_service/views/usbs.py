from ereuse_utils.usb_flash_drive import plugged_usbs
from flask import Response, jsonify, request
from pydash import find
from tinydb import Query, TinyDB
from werkzeug.exceptions import BadRequest, NotFound

USB = Query()


class USBs:
    def __init__(self, app, usbs_path) -> None:
        self.app = app
        self.named_usbs = TinyDB(usbs_path)
        self.client_plugged = {}
        app.add_url_rule('/usbs', view_func=self.view_usbs, methods=['GET'])
        app.add_url_rule('/usbs/name', view_func=self.view_name_usb, methods=['POST'])
        app.add_url_rule('/usbs/plugged/<usb_hid>', view_func=self.view_client_plug, methods=['POST', 'DELETE'])

    def view_usbs(self) -> str:
        return jsonify({
            'plugged': list(plugged_usbs()),
            'named': self.get_all_named_usbs()
        })

    def view_name_usb(self):
        usb = request.get_json()
        name = usb['name']
        usbs_updated = self.named_usbs.update({'name': name}, USB._id == usb['_id'])
        if not usbs_updated:
            # Add new USB to the named_usbs
            usb = find(list(plugged_usbs()), {'_id': usb['_id']})
            if usb is None:
                raise BadRequest('Only already named USB pen-drives can be named without plugging them in. '
                                 'Plug the pen-drive and try again.')
            usb['name'] = name
            self.named_usbs.insert(usb)
        return Response(status=204)

    def get_named_usb(self, serial_number) -> dict:
        usb = self.named_usbs.search(USB.serialNumber == serial_number)
        if not usb:
            raise NotFound('The USB with S/N {} is not named.'.format(serial_number))
        return usb[0]

    def get_all_named_usbs(self):
        return self.named_usbs.all()

    def view_client_plug(self, usb_hid):
        usb = request.get_json()
        if request.method == 'POST':
            self.client_plugged[usb_hid] = usb
        else:  # DELETE
            try:
                del self.client_plugged[usb_hid]
            except KeyError:
                raise NotFound()
        return Response(status=204)
