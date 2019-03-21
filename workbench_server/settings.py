import pathlib
from typing import Type, TypeVar

import ereuse_utils
from boltons.typeutils import classproperty
from flask import current_app, json
from furl import furl

T = TypeVar('T', bound='Settings')


class Settings(ereuse_utils.Dumpeable):
    FILENAME = 'settings.json'

    def write(self):
        # Potentially other processes are reading this file
        # Try not to unnecessarily write to it if the contents
        # are the same -> let's check it first
        saved_one = self.read()
        if self != saved_one:
            with self.file.open('w') as f:
                json.dump(self, f)

    @classmethod
    def read(cls: Type[T]) -> T:
        try:
            with cls.file.open() as f:
                s = json.load(f)
            return cls(**s)
        except FileNotFoundError:
            return cls()

    @classproperty
    def file(cls) -> pathlib.Path:
        return current_app.dir.settings / cls.FILENAME

    def __eq__(self, o: object) -> bool:
        return vars(self) == vars(o)

    def __bool__(self):
        return bool(vars(self))


class WorkbenchSettings(Settings):
    def __init__(self, smart=None, erase=None, eraseSteps=None,
                 eraseLeadingZeros=None, stress=None, install=None, link=None, **kwargs) -> None:
        super().__init__()
        self.smart = smart
        self.erase = erase
        self.erase_steps = eraseSteps
        self.erase_leading_zeros = eraseLeadingZeros
        self.stress = stress
        self.install = install
        self.link = link


class DevicehubConnection(Settings):
    FILENAME = 'dh.json'

    def __init__(self, devicehub: str = None, db: str = None, token: str = None) -> None:
        super().__init__()
        self.devicehub = furl(devicehub)
        self.db = db
        self.token = token

    def __bool__(self):
        return bool(str(self.devicehub))
