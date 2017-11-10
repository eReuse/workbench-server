import json
from time import sleep

from workbench_server.tests.fixtures.phases import phases, phase0, phase5
from workbench_server.tests.test_worker import TestWorker
from workbench_server.worker import Worker


def dummy(worker: Worker, timing=5, add_usb=True, remove_usb=True, install_os=True):
    test = TestWorker()
    test.worker = worker
    test.setUp_dbs()
    for i, phase in enumerate(phases[:-1]):
        sleep(timing)
        print('Phase {}'.format(i))
        test.worker.consume_phase(json.dumps(phase))
    # Link
    if add_usb:
        print('Add USB')
        data = {
            'inventory': phase0['device']['_uuid'],
            'vendor': 'foo',
            'product': 'bar',
            'usb': 'foobar'
        }
        test.worker.add_usb(data)
    if remove_usb:
        sleep(timing * 2)
        print('Remove USB')
        test.worker.del_usb({'inventory': phase0['device']['_uuid']})
    if install_os:
        print('Send to DeviceHub')
        test.worker.consume_phase(json.dumps(phase5))
