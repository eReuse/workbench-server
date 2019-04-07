import datetime
import enum
import json
import pathlib
import uuid as uuid_mod
from contextlib import suppress

import ereuse_utils
from ereuse_utils.naming import Naming
from flask import current_app
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.orm.exc import NoResultFound

from workbench_server.db import db
from workbench_server.settings import WorkbenchSettings


@enum.unique
class ProgressEvents(enum.Enum):
    StressTest = 'StressTest'
    TestDataStorage = 'TestDataStorage'
    EraseBasic = 'EraseBasic'
    EraseSectors = 'EraseSectors'
    Install = 'Install'


@enum.unique
class Phases(enum.Enum):
    """States of the Snapshot"""
    Info = 'Info'
    StressTest = 'StressTest'
    Benchmark = 'Benchmark'
    DataStorage = 'DataStorage'
    Link = 'Link'

    # Upload phases
    ReadyToUpload = 'ReadyToUpload'
    Uploading = 'Uploading'
    Uploaded = 'Uploaded'
    ConnectionError = 'ConnectionError'
    HTTPError = 'HTTPError'

    Error = 'Error'

    @classmethod
    def get_phase_from_progress_event(cls, event: ProgressEvents) -> 'Phases':
        if event == ProgressEvents.StressTest:
            return cls.StressTest
        else:
            return cls.DataStorage

    @classmethod
    def get_phase_from_event(cls, event: str):
        if 'Benchmark' in event:
            return cls.Benchmark


class SnapshotInheritorMixin:
    @declared_attr
    def uuid(cls):
        return db.Column(postgresql.UUID(as_uuid=True),
                         db.ForeignKey(Snapshot.uuid, ondelete='CASCADE'),
                         primary_key=True)


class Snapshot(db.Model):
    uuid = db.Column(postgresql.UUID(as_uuid=True), primary_key=True)
    phase = db.Column(db.Enum(Phases), nullable=False, index=True)
    closed = db.Column(db.TIMESTAMP(timezone=False))
    closed.comment = """A Snapshot that is closed """
    type = db.Column(db.Unicode, nullable=False)

    @declared_attr
    def __mapper_args__(cls):
        """
        Defines inheritance.

        From `the guide <http://docs.sqlalchemy.org/en/latest/orm/
        extensions/declarative/api.html
        #sqlalchemy.ext.declarative.declared_attr>`_
        """
        args = {'polymorphic_identity': cls.__name__}
        if cls.__name__ == 'Snapshot':
            args['polymorphic_on'] = cls.type
        else:
            args['inherit_condition'] = cls.uuid == Snapshot.uuid
        return args

    @classmethod
    def all_client(cls):
        for snapshot in cls.query:
            yield snapshot.data_client()

    def write(self, dir: pathlib.Path = None) -> pathlib.Path:
        dir = dir or current_app.dir.snapshots
        path = self.path(dir)
        with path.open('w') as f:
            json.dump(self.data, f, indent=2, sort_keys=True, cls=ereuse_utils.JSONEncoder)
        return path

    @classmethod
    def one(cls, id: uuid_mod.UUID) -> 'Snapshot':
        return cls.query.filter_by(uuid=id).first_or_404()

    def hid(self) -> str:
        un = 'Unknown'
        device = self.data['device']
        return Naming.hid(device['type'],
                          device['manufacturer'] or un,
                          device['model'] or un,
                          device['serialNumber'] or un)

    def data_client(self):
        s = self.data.copy()
        s['_phase'] = self.phase
        s['_linked'] = False  # todo ??
        return s

    @classmethod
    def get_to_clean(cls):
        """Gets the snapshots that can be cleaned."""
        return cls.query.filter(cls.closed.isnot(None))

    def path(self, dir: pathlib.Path) -> pathlib.Path:
        """Returns the path of the file for a given directory."""
        return dir.joinpath(self.hid() + '.json')

    def delete(self, dir: pathlib.Path):
        self.path(dir).unlink()

    def __repr__(self) -> str:
        return '<Snapshot {} phase={} closed={}>'.format(self.uuid, self.phase, self.closed)


class SnapshotComputer(SnapshotInheritorMixin, Snapshot):
    data = db.Column(MutableDict.as_mutable(postgresql.JSONB), nullable=False)
    data.comment = """The actual Snapshot that is sent to Devicehub."""

    def __init__(self, **kw) -> None:
        super().__init__(**kw)
        self.phase = Phases.Info

    def conditionally_set_phase_from_event(self, event: str):
        phase = Phases.get_phase_from_event(event)
        if phase:
            self.phase = phase

    def close(self, new: dict):
        """Closes a Snapshot, conditionally setting it to upload."""
        assert not self.data['closed']
        for key in 'closed', 'endTime', 'elapsed':
            self.data[key] = new[key]
        assert self.data['closed']
        self.closed = datetime.datetime.now()
        settings = WorkbenchSettings.read()
        # Wait to link if it is set in settings and we are not linked yet
        # Otherwise set to upload
        self.phase = Phases.Link if settings.link and not self.is_linked() else Phases.ReadyToUpload
        self.write()
        flag_modified(self, 'data')

    def set_event(self, event: dict, component: int = None):
        """Sets an event to the device (default) or component defined
        by pos.
        """
        if component is None:
            self.data['device']['events'].append(event)
        else:
            self.data['components'][component]['events'].append(event)
        flag_modified(self, 'data')

    def from_form(self, form: dict):
        """Sets data submitted from a DHC form, conditionally setting it to upload."""
        self.data['device']['tags'] = form.get('tags', [])
        # Always delete old rate
        events = self.data['device']['events']
        with suppress(StopIteration):
            pos = next(i for i, e in enumerate(events) if e['type'] == 'Workbenchrate')
            del events[pos]

        rate = form.get('rate', None)
        if rate:
            events.append(form)

        self.data['description'] = form.get('description', None)

        # If this form submission has some tags and we already finished, set to upload
        if self.phase == Phases.Link and self.is_linked():
            self.phase = Phases.ReadyToUpload
            self.write()
        flag_modified(self, 'data')

    def is_linked(self):
        return bool(len(self.data['device'].get('tags', [])))


class Progress(db.Model):
    DEVICE = -1

    snapshot_uuid = db.Column(postgresql.UUID(as_uuid=True),
                              db.ForeignKey(Snapshot.uuid, ondelete='CASCADE'),
                              primary_key=True)
    component = db.Column(db.SmallInteger, primary_key=True, default=DEVICE)
    component.comment = '"-1" means that is the device. >= 0 means the pos of the component.'
    event = db.Column(db.Enum(ProgressEvents))
    percentage = db.Column(db.SmallInteger)
    total = db.Column(db.SmallInteger)

    snapshot = db.relationship(SnapshotComputer,
                               backref=db.backref('progress',
                                                  lazy=True,
                                                  collection_class=set,
                                                  cascade='all, delete-orphan'),
                               lazy=True)

    # todo delete progerss of snapshots when deleting snapshots

    @classmethod
    def get(cls, uuid, component=DEVICE) -> 'Progress':
        """Gets an already existing Progress or a new one with the
        passed-in parameters.
        """
        # We might get passed-in None
        component = component if component is not None else cls.DEVICE
        snapshot = SnapshotComputer.one(uuid)
        try:
            return cls.query.filter_by(snapshot=snapshot, component=component).one()
        except NoResultFound:
            return cls(snapshot=snapshot, component=component)

    @classmethod
    def set(cls, uuid, component, event, percentage, total):
        progress = cls.get(uuid, component)
        progress.event = ProgressEvents(event)
        progress.percentage = percentage
        progress.total = total
        progress.snapshot.phase = Phases.get_phase_from_progress_event(progress.event)
        return progress
