import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from ereuse_utils.test import AUTH, BASIC, Client
from requests_mock import Mocker

from workbench_server.flaskapp import WorkbenchServer


@pytest.fixture
def app(tmpdir) -> WorkbenchServer:
    app = WorkbenchServer(folder=Path(tmpdir.strpath))
    app.testing = True
    return app


@pytest.fixture
def client(app: WorkbenchServer) -> Client:
    return app.test_client()


def jsonf(file_name: str) -> dict:
    """Gets a json fixture and parses it to a dict."""
    with Path(__file__).parent.joinpath('fixtures').joinpath(file_name + '.json').open() as file:
        return json.load(file)


@pytest.fixture()
def request_mock() -> Mocker:
    """
    Integrates requests-mock with pytest.

    See https://github.com/pytest-dev/pytest/issues/2749#issuecomment-350411895.
    """
    with Mocker() as m:
        yield m


@pytest.fixture()
def fusb() -> (dict, str):
    """Fixture of a plugged-in USB in a Workbench client."""
    return jsonf('usb'), '/usbs/kingston-0014780ee3fbf090d52f1286-dt_101_g2'


@pytest.fixture()
def mock_ip(app: WorkbenchServer):
    """Mocks :meth:`workbench_server.info.Info.local_ip`."""
    app.info.local_ip = MagicMock(return_value='X.X.X.X')


@pytest.fixture()
def mock_snapshot_post(request_mock: Mocker) -> (dict, dict, Mocker):
    """
    Mocks uploading to snapshot (login and upload).
    You will need to POST to /login with returned params.
    """
    params = [
        ('device-hub', 'https://foo.com'),
        ('db', 'db-foo')
    ]
    headers = {AUTH: BASIC.format('FooToken')}
    request_mock.post('https://foo.com/db-foo/snapshot',
                      json={'_id': 'new-snapshot-id'},
                      request_headers=headers)

    return params, headers, request_mock
