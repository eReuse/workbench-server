import json
import sys

from assertpy import assert_that

from workbench_server.tests.fixtures.phases import phases
from workbench_server.tests.test_worker import TestWorker


class TestConsumePhase(TestWorker):
    def test_consume_phases(self):
        """
        Tests all phases when they are all performed
        (not skipped in config) and successful.
        """
        for i, phase in enumerate(phases):
            try:
                self.worker.consume_phase(json.dumps(phase))
                value = self.worker.dbs.redis.get(phase['device']['_uuid'])
                snapshot = json.loads(value.decode())
                assert_that(snapshot['times']).is_length(i + 1)
            except Exception as e:
                print('Error in phase number {}'.format(i), file=sys.stderr)
                raise e
        # We didn't consolidate a JSON file because we have not linked it yet
        assert_that(self.json_from_inventory).raises(AssertionError).when_called_with()
