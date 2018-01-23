import json
from pathlib import Path

import pytest
from ereuse_utils.test import Client
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


def jsonf(file_name) -> dict:
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
