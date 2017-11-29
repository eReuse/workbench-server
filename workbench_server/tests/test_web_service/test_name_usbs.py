import json
from unittest.mock import patch

from assertpy import assert_that

from workbench_server.tests.test_web_service import TestWebService
from workbench_server.tests.test_worker import TestWorker


class TestNameUsbs(TestWebService, TestWorker):

    @patch('usb.core.find')
    def test_name_usb(self, MockFind):
        """Tests naming an USB"""

        # Get a mocked plugged-in USB
        class MockDevice:  # The returned Device from the usbs package
            idProduct = '123'
            product = 'bar'
            serial_number = 'foobar'
            manufacturer = 'foo'

        MockFind.return_value = [MockDevice()]

        response = self.client.get('/usbs')
        assert_that(response.status_code).is_equal_to(200)
        returned_usbs = json.loads(response.data.decode())

        usb = {'_id': '123', 'model': 'bar', 'serialNumber': 'foobar', 'manufacturer': 'foo'}
        assert_that(returned_usbs).is_equal_to({'plugged': [usb], 'named': []})

        # Name the USB
        req = {'_id': '123', 'name': 'Cool Name'}
        response = self.client.post('/usbs/name', data=json.dumps(req), content_type='application/json')
        assert_that(response.status_code).is_equal_to(200)

    def test_name_not_existing_usb(self):
        """Tests naming an USB that has not been named before and it is not plugged."""
        req = {'_id': 'this-id-does-not-exst', 'name': 'Cool Name'}
        response = self.client.post('/usbs/name', data=json.dumps(req), headers={'Accept': 'application/json'},
                                    content_type='application/json')
        assert_that(response.status_code).is_equal_to(400)
        assert_that(response.data.decode()).contains('Only already named USB pen-drives')
