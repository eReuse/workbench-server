from cachetools import TTLCache
from flask import Response, request

from workbench_server import flaskapp


class USBs:
    """
    Keeps a registry of plugged-in Mass Flash Storage USB devices
    (pen-drives) from Workbench clients, allowing clients like DeviceHub
    retrieve such information; and allows clients to name those devices.
    """

    def __init__(self, app: 'flaskapp.WorkbenchServer') -> None:
        self.app = app
        self.client_plugged = TTLCache(maxsize=100, ttl=5)
        """
        Clients that have plugged-in USBs. All USBs that have not
        been reported to still be plugged-in in 5 seconds ore more
        are removed from the dict, keeping the values updated.
        
        Note that `maxsize` is just required, and limits the number
        of plugged-in USBs to 100. Can safely be increased if needed.  
        """
        app.add_url_rule('/usbs/<usb_hid>',
                         view_func=self.view_client_plug,
                         methods={'POST', 'DELETE'})

    def view_client_plug(self, usb_hid: str):
        """
        Tells to WorkbenchServer that a pen-drive has been plugged-in
        in a client. From this moment, the pen-drive will be shown in
        :attr:`.USBs.view_usbs` inside the `plugged` dict property.
        """
        usb = request.get_json()
        if request.method == 'POST':
            self.client_plugged[usb_hid] = usb
        else:  # Delete
            self.client_plugged.pop(usb_hid, None)
        return Response(status=204)

    def get_usbs(self) -> list:
        """
        Get the pen-drives that are plugged in the client
        executing Workbench.
        """

        def get():
            # If we plug / unplug an USB while we are iterating
            # we could get a runtimeError. In that case just try again
            try:
                return tuple(self.client_plugged.values())
            except RuntimeError:
                return get()

        return get()
