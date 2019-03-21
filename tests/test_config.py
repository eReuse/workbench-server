from ereuse_utils.test import Client

from tests.conftest import jsonf


def test_config(client: Client):
    """Tests getting and modifying the config."""
    # Let's get it without any change
    config, _ = client.get('/settings/')
    # todo add assert assert config == {}

    # We upload new config with those values changed
    config_fixture = jsonf('config')
    client.post('/settings/', data=config_fixture, status=204)

    # We get the new config with the values changed
    config, _ = client.get('/settings/')
    assert config == config_fixture
