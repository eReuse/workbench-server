import json

from assertpy import assert_that

from workbench_server.tests.test_web_service import TestWebService


class TestConfig(TestWebService):
    def setUp(self):
        super().setUp()

    def config(self):
        response = self.client.get('/config')
        assert_that(response.status_code).is_equal_to(200)
        return json.loads(response.data.decode())

    def test_get_config(self):
        """Tests getting the config."""
        self.config()

    def test_post_config(self):
        """Tests changing the config."""
        # Default config has IMAGE_NAME and stress empty and as 0
        config = self.config()
        assert_that(config).has_IMAGE_NAME('')
        assert_that(config).has_STRESS(0)
        # We upload new config with those values changed
        config = self.json('model_from_config_web')
        response = self.client.post('/config', data=json.dumps(config), content_type='application/json')
        assert_that(response.status_code).is_equal_to(201)
        # We get the new config with the values changed
        config = self.config()
        assert_that(config).has_IMAGE_NAME('foobar')
        assert_that(config).has_STRESS(40)
