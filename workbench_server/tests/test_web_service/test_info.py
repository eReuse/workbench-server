import json

from assertpy import assert_that

from workbench_server.tests.fixtures.phases import phase0, phase1, phase2, phase3, phase4, phase5
from workbench_server.tests.test_web_service import TestWebService
from workbench_server.tests.test_worker import TestWorker


class TestInfo(TestWebService, TestWorker):
    def info(self) -> dict:
        response = self.client.get('/info')
        assert_that(response.status_code).is_equal_to(200)
        return json.loads(response.data.decode())

    def test_get_info(self):
        """Ensures that the /info endpoint returns the correct values depending on each phase."""
        # emptiness (before performing anything)
        response = self.info()
        assert_that(response).is_equal_to({'usbs': [], 'devices': []})

        # phase 0
        self.worker.consume_phase(json.dumps(phase0))
        response0 = self.info()
        assert_that(response0).contains('devices')
        assert_that(response0['devices']).is_length(1)
        assert_that(response0['devices'][0]).contains('key', 'val')
        assert_that(response0['devices'][0]['val']).has__uuid('ab1dc8d625a14ed09b7a0aa82f98b6e7')
        assert_that(response0['devices'][0]['val']['times']).is_length(1)

        # phase 1
        self.worker.consume_phase(json.dumps(phase1))
        response1 = self.info()
        assert_that(response1['devices']).is_length(1)
        assert_that(response1['devices'][0]['val']['times']).is_length(2)

        # phase 2
        self.worker.consume_phase(json.dumps(phase2))
        response2 = self.info()
        assert_that(response2['devices']).is_length(1)
        assert_that(response2['devices'][0]['val']['times']).is_length(3)

        # phase 3
        self.worker.consume_phase(json.dumps(phase3))
        response3 = self.info()
        assert_that(response3['devices']).is_length(1)
        assert_that(response3['devices'][0]['val']['times']).is_length(4)

        # Add usb while in phase 3
        data = {
            'inventory': phase0['device']['_uuid'],
            'vendor': 'foo',
            'product': 'bar',
            'usb': 'foobar'
        }
        self.worker.add_usb(data)
        response3_usb = self.info()
        assert_that(response3_usb['devices']).is_length(1)
        assert_that(response3_usb['devices'][0]['val']['times']).is_length(4)
        assert_that(response3_usb['usbs']).is_length(1)
        assert_that(response3_usb['usbs'][0]).has_vendor('foo')\
            .has_product('bar').has_usb('foobar').has__uuid(phase3['device']['_uuid'])

        # phase 4
        self.worker.consume_phase(json.dumps(phase4))
        response4 = self.info()
        assert_that(response4['devices']).is_length(1)
        assert_that(response4['devices'][0]['val']['times']).is_length(5)
        self.worker.consume_phase(json.dumps(phase5))

        # phase 5
        response5 = self.info()
        assert_that(response5['devices']).is_length(1)
        assert_that(response5['devices'][0]['val']['times']).is_length(6)
