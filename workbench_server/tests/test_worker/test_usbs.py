import json

from assertpy import assert_that

from workbench_server.tests.fixtures.phases import phase0
from workbench_server.tests.test_worker import TestWorker


class TestUsbs(TestWorker):
    def test_usbs(self):
        # Add the usb
        data = {
            'inventory': phase0['device']['_uuid'],
            'vendor': 'foo',
            'product': 'bar',
            'usb': 'foobar'
        }
        self.worker.add_usb(data)
        usb = self.worker.dbs.usb.get(phase0['device']['_uuid'])
        usb = json.loads(usb.decode())
        assert_that(usb).has_usb('foobar').has_vendor('foo').has_product('bar')
        # Remove the usb
        data = {'inventory': phase0['device']['_uuid']}
        self.worker.del_usb(data)
        uuid = self.worker.dbs.usb.get(phase0['device']['_uuid'])
        assert_that(uuid).is_none()
