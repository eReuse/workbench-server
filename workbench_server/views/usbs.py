from pathlib import Path

from cachetools import TTLCache
from ereuse_utils.usb_flash_drive import plugged_usbs
from flask import Response, jsonify, request
from pydash import find
from tinydb import Query, TinyDB
from werkzeug.exceptions import BadRequest, NotFound

from workbench_server import flaskapp

USB = Query()


class USBs:
    """
    Keeps a registry of plugged-in Mass Flash Storage USB devices (pen-drives) from Workbench clients,
    allowing clients like DeviceHub retrieve such information; and allows clients to name those devices.
    """

    def __init__(self, app: 'flaskapp.WorkbenchServer', settings_path: Path) -> None:
        self.app = app
        self.named_usbs = TinyDB(str(settings_path.joinpath('usbs.json')))
        self.client_plugged = TTLCache(maxsize=150, ttl=5)  # Maxsize is just required, we won't have >150 plugged USB
        """
        Pen-drives plugged on clients. 
        We will auto-remove the pen-drives in 7 seconds if we don't get any signal from the client.
        """
        app.add_url_rule('/usbs', view_func=self.view_usbs, methods=['GET'])
        app.add_url_rule('/usbs/named', view_func=self.view_name_usb, methods=['POST'])
        app.add_url_rule('/usbs/named/<usb_hid>', view_func=self.view_unname_usb, methods=['DELETE'])
        app.add_url_rule('/usbs/plugged/<usb_hid>', view_func=self.view_client_plug, methods=['POST', 'DELETE'])

    def view_usbs(self) -> str:
        """Gets plugged-in and named pen-drives."""
        return jsonify({
            'plugged': list(plugged_usbs()),
            'named': self.get_all_named_usbs()
        })

    def view_name_usb(self):
        """
        Name a pen-drive. From this moment, the name will be appended to the information of the pen-drive in
        :attr:`.USBs.view_usbs`.

        Pen-drive must be plugged-in in the **machine executing WorkbenchServer**.
        """
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

    def view_client_plug(self, usb_hid: str):
        """
        Tells to WorkbenchServer that a pen-drive has been plugged-in in a client.
        From this moment, the pen-drive will be shown in :attr:`.USBs.view_usbs`
        inside the `plugged` dict property.
        """
        usb = request.get_json()
        if request.method == 'POST':
            self.client_plugged[usb_hid] = usb
        else:  # Delete
            try:
                del self.client_plugged[usb_hid]
            except KeyError:
                raise NotFound()
        return Response(status=204)

    def view_unname_usb(self, usb_hid: str):
        self.client_plugged.pop(usb_hid, None)
        return Response(status=204)

    def get_named_usb(self, serial_number: str) -> dict:
        usb = self.named_usbs.search(USB.serialNumber == serial_number)
        if not usb:
            raise NotFound('The USB with S/N {} is not named.'.format(serial_number))
        return usb[0]

    def get_all_named_usbs(self):
        return self.named_usbs.all()