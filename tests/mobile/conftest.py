import os
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

PATH = Path(__file__).parent / 'files'  # type: Path


def read_file(model, name):
    file = PATH / '{}.{}.txt'.format(name, model)  # type: Path
    return file.read_text().strip().replace('\t', '')


def _return_file_factory(model: str):
    def _return_file(*args, **kwargs):
        if '/proc/cpuinfo' in args:
            return read_file(model, 'cpuinfo')
        elif '/sys/devices/system/cpu' in args:
            return read_file(model, 'cpu-ls')
        elif '/proc/meminfo' in args:
            return read_file(model, 'meminfo')
        elif 'battery' in args:
            return read_file(model, 'battery.dumpsys')
        elif 'dumpsys' in args:
            return read_file(model, 'dumpsys')
        elif 'ip' in args:
            return read_file(model, 'ip')
        elif 'settings' in args:
            return read_file(model, 'bluetooth_address')
        elif 'getprop' in args:
            return read_file(model, 'getprop')
        elif 'iphonesubinfo' in args and 1 in args:
            return read_file(model, 'iphonesubinfo.1')
        elif 'iphonesubinfo' in args and 16 in args:
            return read_file(model, 'iphonesubinfo.1')
        elif '/data' in args:
            return read_file(model, 'data.df')
        elif '/system' in args:
            return read_file(model, 'system.df')
        raise AssertionError('Invalid args {}'.format(args))

    return _return_file


def _pull_factory(model: str):
    def _pull(_, destination: str):
        # os.rename(str(PATH.joinpath('framework-res.{}.apk'.format(model))),
        #          destination + '/framework-res.apk')
        shutil.copy(str(PATH.joinpath('framework-res.{}.apk'.format(model))),
                  destination + '/framework-res.apk')
    return _pull


@pytest.fixture()
def mocked_adb():
    """Fixture that mocks the ADB class returning fixture files instead
    of connecting to an adb service itself.
    """

    class MockedAdb():
        def __init__(self, *args, **kwargs) -> None:
            super().__init__()

        @property
        def dumpsys(self):
            return self.shell('dumpsys')

        @classmethod
        def devices(cls):
            return PATH.joinpath('adb-devices.txt').read_text()

        @classmethod
        def set(cls, model: str):
            cls.shell = MagicMock(side_effect=_return_file_factory(model))
            cls.pull = MagicMock(side_effect=_pull_factory(model))

    with patch('workbench_server.mobile.models.Adb', new=MockedAdb) as mocked_adb:
        yield mocked_adb
