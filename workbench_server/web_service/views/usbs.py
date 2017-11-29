import usb.core
import usb.util
from flask import Response, jsonify, request
from pydash import find
from tinydb import JSONStorage, Query, TinyDB
from tinydb.middlewares import CachingMiddleware
from usb import CLASS_MASS_STORAGE
from werkzeug.exceptions import BadRequest, NotFound

USB = Query()


class USBs:
    def __init__(self, app, usbs_path) -> None:
        self.app = app
        self.named_usbs = TinyDB(usbs_path)
        app.add_url_rule('/usbs', view_func=self.view_usbs, methods=['GET'])
        app.add_url_rule('/usbs/name', view_func=self.view_name_usb, methods=['POST'])

    def view_usbs(self) -> str:
        return jsonify({
            'plugged': list(self.plugged_usbs()),
            'named': self.get_all_named_usbs()
        })

    def plugged_usbs(self) -> map:
        class FindPenDrives(object):
            # From https://github.com/pyusb/pyusb/blob/master/docs/tutorial.rst
            def __init__(self, class_):
                self._class = class_

            def __call__(self, device):
                # first, let's check the device
                if device.bDeviceClass == self._class:
                    return True
                # ok, transverse all devices to find an
                # interface that matches our class
                for cfg in device:
                    # find_descriptor: what's it?
                    intf = usb.util.find_descriptor(
                        cfg,
                        bInterfaceClass=self._class
                    )
                    if intf is not None:
                        return True

                return False

        def get_pendrive(pen: usb.Device):
            return {
                '_id': pen.idProduct,
                'model': pen.product,
                'serialNumber': pen.serial_number,  # Hook on this
                'manufacturer': pen.manufacturer
            }

        return map(get_pendrive, usb.core.find(find_all=1, custom_match=FindPenDrives(CLASS_MASS_STORAGE)))

    def view_name_usb(self):
        usb = request.get_json()
        name = usb['name']
        usbs_updated = self.named_usbs.update({'name': name}, USB._id == usb['_id'])
        if not usbs_updated:
            # Add new USB to the named_usbs
            usb = find(list(self.plugged_usbs()), {'_id': usb['_id']})
            if usb is None:
                raise BadRequest('Only already named USB pen-drives can be named without plugging them in. '
                                 'Plug the pen-drive and try again.')
            usb['name'] = name
            self.named_usbs.insert(usb)
        return Response(status=200)

    def get_named_usb(self, serial_number) -> dict:
        usb = self.named_usbs.search(USB.serialNumber == serial_number)
        if not usb:
            raise NotFound('The USB with S/N {} is not named.'.format(serial_number))
        return usb[0]

    def get_all_named_usbs(self):
        return self.named_usbs.all()
