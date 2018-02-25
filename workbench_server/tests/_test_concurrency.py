from datetime import timedelta
from itertools import chain
from multiprocessing import Process
from random import randint, random
from time import sleep
from typing import List
from uuid import uuid4

import pytest
import urllib3
from ereuse_utils import now
from requests_mock import Mocker
from requests_toolbelt.sessions import BaseUrlSession

from workbench_server.flaskapp import WorkbenchServer

PORT = 5001
FLASK_BASE_URL = 'http://localhost:{}'.format(PORT)
WORKBENCHS = 120
WEBS = 20


def workbench(phases: List[dict], fusb: (dict, str)):
    """Workbench client"""
    usb, usb_uri = fusb
    usb = usb.copy()
    usb['_uuid'] = uuid = str(uuid4())
    server = BaseUrlSession(base_url=FLASK_BASE_URL)
    server.verify = False
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    for phase in phases:
        phase['_uuid'] = uuid
        before = now()
        r = server.patch('/snapshots/{}'.format(uuid), json=phase)
        assert r.status_code == 204
        assert now() - before < timedelta(seconds=10)
        sleep(random())
        before = now()
        r = server.post(usb_uri, json=usb)
        assert r.status_code == 204
        assert now() - before < timedelta(seconds=10)
        sleep(randint(0, 5))
    sleep(randint(0, 2))
    r = server.patch('/snapshots/{}'.format(uuid), json={'device': {'_id': uuid}, '_linked': True})
    assert r.status_code == 204, r.json()


def web(dh_params: dict, dh_headers: dict):
    """Web client"""
    server = BaseUrlSession(base_url=FLASK_BASE_URL)
    server.params.update(dh_params)
    server.headers.update(dh_headers)
    server.verify = False
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    while True:
        sleep(randint(1, 3))
        before = now()
        r = server.get('/info')
        assert r.status_code == 200
        assert now() - before < timedelta(seconds=10)


@pytest.fixture()
def server():
    def _run_server():
        # We need to instantiate WorkbenchServer in the same process
        # where it is run
        app = WorkbenchServer()
        app.run(threaded=True, port=PORT, use_reloader=False, debug=True)

    p = Process(target=_run_server, name='WorkbenchServer')
    p.start()
    yield p
    p.terminate()


@pytest.mark.usefixtures('mock_ip', 'server')
def test_concurrency(fphases: (list, str), fusb: (dict, str),
                     mock_snapshot_post: (dict, dict, Mocker)):
    """
    Stresses WorkbenchServer by emulating requests of multiple Workbench
    clients and web clients, in a multiprocess and multithreaded
    environment.

    Multithreaded idea from `this blog <http://www.prschmid.com/2013/01/
    multi-threaded-unit-test-for-flask-rest.html>`_.
    """
    dh_params, dh_headers, mocked_snapshot = mock_snapshot_post  # type: dict,dict,Mocker
    mocked_snapshot._real_http = True
    webs = tuple(Process(target=web, args=(dh_params, dh_headers), daemon=True)
                 for _ in range(WEBS))
    wargs = (fphases[0], fusb)
    workbenchs = tuple(Process(target=workbench, args=wargs) for _ in range(WORKBENCHS // 2))
    for client in chain(workbenchs, webs):
        client.start()
    sleep(2)
    # We re-create them after
    new_workbenchs = tuple(Process(target=workbench, args=wargs) for _ in range(WORKBENCHS // 2))
    for client in new_workbenchs:
        client.start()
    for workbench_client in chain(workbenchs, new_workbenchs):
        workbench_client.join()
