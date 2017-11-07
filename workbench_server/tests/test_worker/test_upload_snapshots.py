import json

import requests_mock
from assertpy import assert_that
from requests import ConnectTimeout
from requests_mock import Mocker

from workbench_server.tests.test_worker import TestWorker


class TestUploadSnapshots(TestWorker):
    def setUp(self):
        super().setUp()
        self.snapshot = self.json('snapshot')
        self.worker.dbs.consolidated.set(self.snapshot['_uuid'], json.dumps(self.snapshot))
        self.HOST = self.worker.device_hub['host']

    @requests_mock.mock()
    def test_upload_snapshots_success(self, m: Mocker):
        """Tests the successful uploading of a Snapshot, performing login first and then uploading the event."""
        account = self.json('account')
        m.post('{}/login'.format(self.HOST), json=account)
        m.post('{}/db1/events/devices/snapshot'.format(self.HOST), json={'status': 'OK'},
               request_headers={'Authentication': 'Basic {}'.format(account['token'])})

        self.worker.upload_snapshots()

        assert_that(m.call_count).is_equal_to(2)  # login and post snapshot
        # We have removed the snapshot from the "to be uploaded" db
        assert_that(self.worker.dbs.consolidated.keys('*')).is_length(0)
        # We have added the json to the "uploaded" db
        successful_snapshots = self.worker.dbs.uploaded.mget(self.worker.dbs.uploaded.keys('*'))
        assert_that(json.loads(successful_snapshots[0].decode())).is_equal_to(self.snapshot)

    @requests_mock.mock()
    def test_upload_snapshots_wrong_login(self, m: Mocker):
        """
        Ensures that no action is taken when the login credentials are wrong
        (which means that celery will retry again later)
        """
        m.post('{}/login'.format(self.HOST), json={}, status_code=422)

        self.worker.upload_snapshots()

        assert_that(m.call_count).is_equal_to(1)
        # The snapshot stays in the consolidated database
        #  so we can try to upload it the next time
        assert_that(self.worker.dbs.consolidated.keys('*')).is_length(1)
        assert_that(self.worker.dbs.uploaded.keys('*')).is_length(0)
        assert_that(self.worker.dbs.upload_errors.keys('*')).is_length(0)

    @requests_mock.mock()
    def test_upload_snapshots_no_connection(self, m: Mocker):
        """
        Ensures that no action is taken when there is an exception in the request (like no connection)
        (which means that celery will retry again later)
        """
        # Exception in login
        m.post('{}/login'.format(self.HOST), exc=ConnectTimeout)
        self.worker.upload_snapshots()
        # No exception bubbles so celery will try later

        # Exception when uploading snapshot
        account = self.json('account')
        m.post('{}/login'.format(self.HOST), json=account)
        m.post('{}/db1/events/devices/snapshot'.format(self.HOST), exc=ConnectTimeout)
        # No exception bubbles neither so celery will try later

        # The snapshot stays in the consolidated database
        #  so we can try to upload it the next time
        assert_that(self.worker.dbs.consolidated.keys('*')).is_length(1)
        assert_that(self.worker.dbs.uploaded.keys('*')).is_length(0)
        assert_that(self.worker.dbs.upload_errors.keys('*')).is_length(0)
