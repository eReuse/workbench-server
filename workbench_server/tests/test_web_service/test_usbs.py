import json
from unittest.mock import patch

from assertpy import assert_that

from workbench_server.tests.fixtures.phases import phase0
from workbench_server.tests.test_web_service import TestWebService
from workbench_server.tests.test_worker import TestWorker


class TestNameUsbs(TestWebService, TestWorker):
    @patch('usb.core.find')
    def test_name_usb(self, MockFind):
        """Tests naming an USB"""

        # Get a mocked plugged-in USB
        class MockDevice:  # The returned Device from the usbs package
            product = 'bar'
            serial_number = 'foobar     '  # Sometimes we can get some extra spaces...
            manufacturer = 'foo'
            idVendor = 123
            idProduct = 456

        MockFind.return_value = [MockDevice()]

        response = self.client.get('/usbs')
        assert_that(response.status_code).is_equal_to(200)
        returned_usbs = json.loads(response.data.decode())

        usb = {
            'manufacturer': 'foo',
            'vendorId': 123,
            'serialNumber': 'foobar',
            'model': 'bar',
            'productId': 456,
            '_id': 'foo-bar-foobar',
            '@type': 'USBFlashDrive',
            'hid': 'foo-bar-foobar'
        }
        assert_that(returned_usbs).is_equal_to({'plugged': [usb], 'named': []})

        # Name the USB
        req = {'_id': 'foo-bar-foobar', 'name': 'Cool Name'}
        response = self.client.post('/usbs/name', data=json.dumps(req), content_type=self.CONTENT_TYPE_JSON)
        assert_that(response.status_code).is_equal_to(204)

    def test_name_not_existing_usb(self):
        """Tests naming an USB that has not been named before and it is not plugged."""
        req = {'_id': 'this-id-does-not-exst', 'name': 'Cool Name'}
        response = self.client.post('/usbs/name', data=json.dumps(req), headers=self.HEADERS_ACCEPT_JSON,
                                    content_type=self.CONTENT_TYPE_JSON)
        assert_that(response.status_code).is_equal_to(400)
        assert_that(response.data.decode()).contains('Only already named USB pen-drives')

    def test_plugging_usbs_in_clients(self):
        # Add the usb
        uuid = phase0['device']['_uuid']
        input_pen = {
            'vendorId': 2385,
            'serialNumber': '001CC0EC2F18F090B5F71524',
            'hid': 'Kingston-DT 101 G2-001cc0ec2f18f090b5f71524',
            'productId': 5698,
            '_uuid': uuid,
            'model': 'DT 101 G2',
            '_id': 'Kingston-DT 101 G2-001cc0ec2f18f090b5f71524',
            '@type': 'USBFlashDrive',
            'manufacturer': 'Kingston'
        }
        response = self.client.post('/usbs/plugged/{}'.format(input_pen['_id']), data=json.dumps(input_pen),
                                    headers=self.HEADERS_ACCEPT_JSON, content_type=self.CONTENT_TYPE_JSON)
        assert_that(response.status_code).is_equal_to(204)
        assert_that(self.app.usbs.client_plugged).contains(input_pen['_id'])
        pen = self.app.usbs.client_plugged[input_pen['_id']]
        assert_that(pen).has_serialNumber('001CC0EC2F18F090B5F71524') \
            .has__id('Kingston-DT 101 G2-001cc0ec2f18f090b5f71524')
        # Remove the usb
        response = self.client.delete('/usbs/plugged/{}'.format(input_pen['_id']))
        assert_that(response.status_code).is_equal_to(204)
        assert_that(self.app.usbs.client_plugged).does_not_contain(input_pen['_id'])
