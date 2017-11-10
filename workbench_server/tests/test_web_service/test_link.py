import json

from assertpy import assert_that

from workbench_server.tests.fixtures.phases import phase0
from workbench_server.tests.test_web_service import TestWebService
from workbench_server.tests.test_worker import TestWorker


class TestLink(TestWebService, TestWorker):
    def test_link(self):
        self.worker.consume_phase(json.dumps(phase0))  # We need at least phase0
        device = {
            '_uuid': phase0['device']['_uuid'],  # This is passed-in by the client
            '_id': '123',
            'gid': 'gid1',
            'device_type': 'Computer',
            'visual_grade': 'A',
            'functional_grade': 'B',
            'comment': 'comment1'
        }
        self.client.post('/link', data=json.dumps(device), content_type='application/json')
        info = self.client.get('/info')
        snapshot = json.loads(info.data.decode())['devices'][0]['val']

        # todo This is a bug, as _id and gid should be in the device field
        # Devicehub is aware of this limitation and fixes it there
        assert_that(snapshot).has__id('123').has_gid('gid1')
        # this is where all fields should be in
        assert_that(snapshot['device']).has_type('Computer')
