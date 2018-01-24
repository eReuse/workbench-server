from contextlib import suppress

from cachetools import TTLCache
from ereuse_utils.usb_flash_drive import plugged_usbs
from flask import Response, jsonify, request
from prwlock import RWLock
from pydash import find
from pymongo.collection import Collection
from werkzeug.exceptions import BadRequest

from workbench_server import flaskapp


class USBs:
    """
    Keeps a registry of plugged-in Mass Flash Storage USB devices
    (pen-drives) from Workbench clients, allowing clients like DeviceHub
    retrieve such information; and allows clients to name those devices.
    """

    def __init__(self, app: 'flaskapp.WorkbenchServer') -> None:
        self.app = app
        self.named_usbs = app.mongo_db.named_usbs  # type: Collection
        self.client_plugged = TTLCache(maxsize=100, ttl=5)
        """
        Clients that have plugged-in USBs. All USBs that have not
        been reported to still be plugged-in in 5 seconds ore more
        are removed from the dict, keeping the values updated.
        
        Note that `maxsize` is just required, and limits the number
        of plugged-in USBs to 100. Can safely be increased if needed.  
        """
        self.client_plugged_lock = RWLock()
        """
        Pen-drives plugged on clients. 
        We will auto-remove the pen-drives in 7 seconds if we don't
        get any signal from the client.
        """
        app.add_url_rule('/usbs', view_func=self.view_usbs, methods={'GET'})
        app.add_url_rule('/usbs/named', view_func=self.view_name_usb, methods={'POST'})
        app.add_url_rule('/usbs/named/<usb_hid>', view_func=self.view_unname_usb,
                         methods={'DELETE'})
        app.add_url_rule('/usbs/plugged/<usb_hid>', view_func=self.view_client_plug,
                         methods={'POST', 'DELETE'})

    def view_usbs(self) -> str:
        """Gets plugged-in and named pen-drives."""
        return jsonify({
            'plugged': list(plugged_usbs()),
            'named': self.get_all_named_usbs()
        })

    def view_name_usb(self):
        """
        Name a pen-drive. From this moment, the name will be appended to
        the information of the pen-drive in :attr:`.USBs.view_usbs`.

        Pen-drive must be plugged-in in the
        **machine executing WorkbenchServer**.
        """
        incoming_usb = request.get_json()
        name = incoming_usb['name']
        result = self.named_usbs.update_one({'_id': incoming_usb['_id']}, update={'name': name})
        if result.modified_count == 0:
            # Add new USB to the named_usbs
            usb = find(list(plugged_usbs()), {'_id': incoming_usb['_id']})
            if usb is None:
                raise BadRequest('Only already named USB pen-drives can be named without '
                                 'plugging them in. Plug the pen-drive and try again.')
            usb['name'] = name
            self.named_usbs.insert_one(usb)
        return Response(status=204)

    def view_client_plug(self, usb_hid: str):
        """
        Tells to WorkbenchServer that a pen-drive has been plugged-in
        in a client. From this moment, the pen-drive will be shown in
        :attr:`.USBs.view_usbs` inside the `plugged` dict property.
        """
        usb = request.get_json()
        if request.method == 'POST':
            if usb_hid in self.client_plugged:
                self.client_plugged[usb_hid] = usb
            else:
                # Only lock if we need to create a new value
                # as we are changing the size of the dict
                with self.client_plugged_lock.writer_lock():
                    self.client_plugged[usb_hid] = usb
        else:  # Delete
            with suppress(KeyError):
                with self.client_plugged_lock.writer_lock():
                    del self.client_plugged[usb_hid]
        return Response(status=204)

    def view_unname_usb(self, usb_hid: str):
        """Removes the USB from the named list."""
        self.client_plugged.pop(usb_hid, None)
        return Response(status=204)

    def get_all_named_usbs(self) -> list:
        return list(self.named_usbs.find())

    def get_client_plugged_usbs(self) -> list:
        """
        Get the pen-drives that are plugged in the client
        executing Workbench.
        """

        def add_usb_name(usb):
            named_usb = self.named_usbs.find_one({'serialNumber': usb['serialNumber']})
            if named_usb:
                usb['name'] = named_usb['name']
            return usb

        with self.client_plugged_lock.reader_lock():
            usbs = list(self.client_plugged.values())
        return [add_usb_name(usb) for usb in usbs]
