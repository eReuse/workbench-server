import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from ereuse_utils.test import AUTH, BASIC, Client
from requests_mock import Mocker

from workbench_server.db import db
from workbench_server.flaskapp import WorkbenchServer
from workbench_server.manager import Manager


@pytest.fixture
def app(tmpdir, mock_snapshot_post: (dict, dict, Mocker)) -> WorkbenchServer:
    Manager.SLEEP = 1
    WorkbenchServer.DATABASE_URI = 'postgresql://dhub:ereuse@localhost/ws_test'
    app = WorkbenchServer(folder=Path(tmpdir.strpath))
    app.testing = True
    with app.app_context():
        app.init_db()
    app.init_manager()
    app.init_mobile()
    try:
        yield app
    finally:
        with app.app_context():
            db.drop_all()


@pytest.fixture
def client(app: WorkbenchServer) -> Client:
    return app.test_client()


def jsonf(name: str, dir='fixtures') -> dict:
    """Gets a json fixture and parses it to a dict."""
    with Path(__file__).parent.joinpath(dir).joinpath(name + '.json').open() as file:
        return json.load(file)


def phase(name: str) -> dict:
    path = Path(__file__).parent.parent / 'workbench_server' / 'phases' / (name + '.json')
    with path.open() as f:
        return json.load(f)


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
        ('db', 'bar')
    ]
    headers = {AUTH: BASIC.format('e376fc02-d312-4ea4-8f12-23d7eb4730ff')}
    request_mock.post('https://foo.com/bar/events/',
                      status_code=201,
                      json={'id': 'new-snapshot-id'},
                      request_headers=headers)

    return params, headers, request_mock
