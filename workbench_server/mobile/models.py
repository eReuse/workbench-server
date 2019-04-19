import datetime
import json
import logging
import math
import pathlib
import tempfile
import uuid
from contextlib import suppress
from enum import Enum
from typing import Any
from xml.etree import ElementTree

import bitmath
import yaml
from ereuse_utils import DumpeableModel, cmd, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy.orm.exc import NoResultFound

from workbench_server.db import db
from workbench_server.models import Phases, Snapshot, SnapshotInheritorMixin


class Adb:
    def __init__(self, serial_number: str) -> None:
        self.serial_number = serial_number
        self.d = 'adb', '-s', self.serial_number
        self.sh = self.d + ('shell',)
        self.dumpsys = self.shell('dumpsys')

    def shell(self, *params, **kwargs) -> str:
        out = cmd.run(*self.sh, *params, **kwargs).stdout  # type: str
        return out.strip().replace('\t', '')

    def pull(self, origin, destination):
        cmd.run(*self.d, 'pull', origin, destination)

    @classmethod
    def devices(cls) -> str:
        return cmd.run('adb', 'devices').stdout


class SnapshotMobile(SnapshotInheritorMixin, Snapshot):
    device = db.relationship('Mobile',
                             cascade='all, delete-orphan',
                             single_parent=True,
                             uselist=False)

    @property
    def data(self):
        device = json.loads(self.device.to_json())  # type: dict
        return {
            'type': 'Snapshot',
            'software': 'WorkbenchAndroid',
            'device': device,
            'components': device.pop('components', []),  # todo remove default
            'uuid': self.uuid,
            'closed': bool(self.closed),
            'endTime': self.closed
        }

    @classmethod
    def new(cls) -> 'SnapshotMobile':
        lines = Adb.devices().splitlines()
        for line in lines[1:]:
            try:
                sn, _ = line.split()
            except ValueError:
                pass
            else:
                if sn:
                    try:
                        Mobile.get(sn)
                    except NoResultFound:
                        return cls(sn)
        raise NoDevice()

    def from_form(self, form: dict):
        self.device.tags.clear()
        self.device.tags.update(Tag(id=t['id']) for t in form.get('tags', []))
        self.device.events.clear()
        rate = form.get('rate', None)
        if rate:
            event = WorkbenchRate(appearanceRange=rate['appearanceRange'],
                                  functionalityRange=rate['functionalityRange'])
            self.device.events.add(event)

        super().from_form(form)

    def is_linked(self):
        return bool(len(self.device.tags))

    def __init__(self, serial_number: str):
        super().__init__(device=Mobile(serial_number=serial_number),
                         phase=Phases.Info,
                         uuid=uuid.uuid4())

    def run(self, jsons: pathlib.Path):
        self.device.run()
        self.closed = datetime.datetime.now()
        self.phase = Phases.Link
        self.write(jsons)

    def __repr__(self) -> str:
        return '<Snapshot {0.uuid} Mobile {0.device}> '.format(self)


class Mobile(db.Model, DumpeableModel):
    # Device fields
    serial_number = db.Column(db.Unicode, primary_key=True)
    model = db.Column(db.Unicode)
    manufacturer = db.Column(db.Unicode)
    variant = db.Column(db.Unicode)
    # Mobile fields
    imei = db.Column(db.BigInteger)
    ram_size = db.Column(db.Integer)
    data_storage_size = db.Column(db.Integer)

    snapshot_id = db.Column(postgresql.UUID(as_uuid=True),
                            db.ForeignKey(SnapshotMobile.uuid, ondelete='CASCADE'),
                            unique=True)

    @classmethod
    def get(cls, serial_number: str):
        return cls.query.filter_by(serial_number=serial_number).one()

    def run(self):
        R = 'ro.product.'
        self._adb = Adb(self.serial_number)
        props = self._get_properties()
        # Although the model should be more the brand
        # Is the only really reliable one with the "Supported Play Store devices"
        self.model = get_prop(props, R + 'model')
        self.variant = get_prop(props, R + 'subdevice', get_prop(props, R + 'device'))
        self.manufacturer = get_prop(props, R + 'manufacturer')

        self.imei = None
        with suppress(NoImei):
            self.imei = self._imei(props)

        # RAM
        meminfo = self._adb.shell('cat', '/proc/meminfo')
        self.ram_size = next(text.numbers(next(text.grep(meminfo, 'MemTotal')))) // 1000

        # Data storage
        # todo it only takes account the /data partition as it is the bigger
        data_storage_size = bitmath.parse_string_unsafe(
            self._adb.shell('df -h', '/data').splitlines()[-1].split()[1]
        ) + bitmath.parse_string_unsafe(
            self._adb.shell('df -h', '/system').splitlines()[-1].split()[1]
        )
        self.data_storage_size = int(data_storage_size.to_MB())

        logging.debug('Data Storage for %s', self)

        self.components.append(Processor(self._adb, props))
        self.components.append(GraphicCard(self._adb))
        self.components.append(Display(self._adb))
        self.components.append(Battery(self._adb))
        self.components.extend(Camera.new(self._adb))

    def _get_properties(self) -> list:
        return self._adb.shell('getprop').replace('[', '').replace(']', '').splitlines()

    def _imei(self, props):
        # https://stackoverflow.com/questions/6852106/is-there-an-android-shell-or-adb-command-that-i-could-use-to-get-a-devices-imei/37940140#37940140
        cmd = 'service', 'call', 'iphonesubinfo'
        imei = self._adb.shell(*cmd, 1)
        if not imei:
            imei = self._adb.shell(*cmd, 16)
        try:
            _, i0, _, i1, _, i2, *_ = imei.split('\'')
            imei = i0 + i1 + i2
            imei = imei.replace('.', '').strip()
            return int(imei)
        except ValueError:
            try:
                # Android 2.X can have an imei property
                return int(get_prop(props, 'ro.gsm.imei'))
            except Exception:
                raise NoImei()

    def dump(self):
        d = super().dump()
        d['components'] = [c.dump() for c in self.components]
        d['type'] = 'Mobile'
        return d

    def __eq__(self, o: object) -> bool:
        if isinstance(o, Mobile):
            return self.serial_number == o.serial_number
        if isinstance(o, str):
            return self.serial_number == o
        else:
            return super().__eq__(o)

    def __hash__(self) -> int:
        return hash(self.serial_number)

    def __repr__(self) -> str:
        return '<Mobile {0.serial_number} model: {0.model}> '.format(self)


def dump_class_name_as_type(cls):
    def dump(self):
        d = super(cls, self).dump()
        d['type'] = self.__class__.__name__
        return d

    cls.dump = dump
    return cls


@dump_class_name_as_type
class Tag(db.Model, DumpeableModel):
    id = db.Column(db.Unicode, primary_key=True)
    _mobile_sn = db.Column('mobile_sn',
                           db.Unicode,
                           db.ForeignKey(Mobile.serial_number, ondelete='CASCADE'))
    _device = db.relationship(Mobile,
                              backref=db.backref('tags',
                                                 collection_class=set,
                                                 cascade='all, delete-orphan'))


@dump_class_name_as_type
class WorkbenchRate(db.Model, DumpeableModel):
    _mobile_sn = db.Column('mobile_sn',
                           db.Unicode,
                           db.ForeignKey(Mobile.serial_number, ondelete='CASCADE'),
                           primary_key=True)
    _device = db.relationship(Mobile,
                              backref=db.backref('events',
                                                 collection_class=set,
                                                 cascade='all, delete-orphan'))
    appearanceRange = db.Column(db.Unicode(1))
    functionalityRange = db.Column(db.Unicode(1))


class NoImei(Exception):
    pass


class Component(db.Model, DumpeableModel):
    _mobile_sn = db.Column('mobile_sn',
                           db.Unicode,
                           db.ForeignKey(Mobile.serial_number, ondelete='CASCADE'),
                           primary_key=True)
    _num = db.Column('num', db.SmallInteger, primary_key=True)
    type = db.Column(db.Unicode, nullable=False, index=True)
    model = db.Column(db.Unicode)
    manufacturer = db.Column(db.Unicode)

    _device = db.relationship(Mobile,
                              backref=db.backref('components',
                                                 collection_class=ordering_list('_num'),
                                                 lazy='joined',
                                                 order_by=_num,
                                                 cascade='all, delete-orphan'))

    @declared_attr
    def __mapper_args__(cls):
        """
        Defines inheritance.

        From `the guide <http://docs.sqlalchemy.org/en/latest/orm/
        extensions/declarative/api.html
        #sqlalchemy.ext.declarative.declared_attr>`_
        """
        args = {'polymorphic_identity': cls.__name__}
        if cls.__name__ == 'Component':
            args['polymorphic_on'] = cls.type
        else:
            args['inherit_condition'] = (cls._mobile_sn == Component._mobile_sn) & \
                                        (cls._num == Component._num)
        return args

    def __repr__(self) -> str:
        return '<Component {0._num}: {0.__class__.__name__}>'.format(self)


class InheritanceMixin:
    @declared_attr
    def _mobile_sn(cls):
        return db.Column('mobile_sn', db.Unicode, primary_key=True)

    @declared_attr
    def _num(cls):
        return db.Column('num', db.SmallInteger, primary_key=True)

    @declared_attr
    def __table__args(cls):
        return (
            db.ForeignKeyConstraint(
                ['mobile_sn', 'num'],
                ['component.mobile_sn', 'component.num'],
                ondelete='CASCADE'
            ),
        )


class Processor(InheritanceMixin, Component):
    cores = db.Column(db.Integer)
    abi = db.Column(db.Unicode)

    def __init__(self, adb, props) -> None:
        super().__init__()

        # Processor
        cpuinfo = adb.shell('cat', '/proc/cpuinfo').splitlines()
        self.model = get_prop(cpuinfo, 'Hardware')
        self.cores = len(tuple(text.numbers(adb.shell('ls', '/sys/devices/system/cpu'))))
        self.abi = get_prop(props, 'ro.product.cpu.abi')
        logging.debug('Processor %s', self)


class GraphicCard(InheritanceMixin, Component):
    def __init__(self, adb) -> None:
        super().__init__()
        gpu = next(text.grep(adb.dumpsys, 'GLES:'))
        manufacturer, model, *_ = gpu.split(':')[1].split(', ')
        self.manufacturer = manufacturer.strip()
        self.model = model.strip()
        logging.debug('Graphic Card %s', self)


class Display(InheritanceMixin, Component):
    size = db.Column(db.Float(decimal_return_scale=2))
    resolution_width = db.Column(db.SmallInteger)
    resolution_height = db.Column(db.SmallInteger)
    refresh_rate = db.Column(db.SmallInteger)
    touchable = db.Column(db.Boolean)

    def __init__(self, adb: Adb) -> None:
        display_info = next(text.grep(adb.dumpsys, 'PhysicalDisplayInfo'))
        self.resolution_width, self.resolution_height, self.refresh_rate, _internal_density, \
        density_width, density_height, *_ = text.numbers(display_info)

        density_width = int(density_width)
        density_height = int(density_height)
        self.refresh_rate = int(self.refresh_rate)

        self.size = round(math.sqrt(
            (self.resolution_width / density_width) ** _internal_density +
            (self.resolution_height / density_height) ** _internal_density
        ), ndigits=2)
        """Size. From https://stackoverflow.com/a/19446138/2710757."""
        self.touchable = True
        logging.debug('Display %s', self)


class Battery(InheritanceMixin, Component):
    wireless = db.Column(db.Boolean)
    technology = db.Column(db.Unicode)
    size = db.Column(db.Integer, nullable=False)
    events = db.relationship('MeasureBattery',
                             cascade='all, delete-orphan',
                             primaryjoin=lambda: (
                                     (Battery._mobile_sn == MeasureBattery._battery_sn) &
                                     (Battery._num == MeasureBattery._num)
                             ),
                             collection_class=set)

    def __init__(self, adb: Adb) -> None:
        props = adb.shell('dumpsys', 'battery').splitlines()
        self.wireless = get_prop(props, 'Wireless powered')
        self.technology = get_prop(props, 'technology')
        self.size = self.get_size(adb)
        with suppress(NoMeasure):
            self.events.add(MeasureBattery(adb, props))
        logging.debug('Battery %s', self)

    @staticmethod
    def get_size(adb: Adb):
        """Gets battery size."""
        # From https://android.stackexchange.com/a/145798
        with tempfile.TemporaryDirectory() as tmpdirname:
            dir = pathlib.Path(tmpdirname)
            apk = dir / 'result'
            adb.pull('system/framework/framework-res.apk', tmpdirname)
            cmd.run('java', '-jar', pathlib.Path(__file__).parent / 'apktool_2.4.0.jar',
                    'd', dir / 'framework-res.apk',
                    '-o', apk)
            root = ElementTree.parse(str(apk / 'res' / 'xml' / 'power_profile.xml'))
            return next(int(i.text) for i in root.findall('item')
                        if i.get('name') == 'battery.capacity')


@dump_class_name_as_type
class MeasureBattery(db.Model, DumpeableModel):
    class BatteryHealth(Enum):
        """The battery health status as in Android."""
        Unknown = 1
        Good = 2
        Overheat = 3
        Dead = 4
        OverVoltage = 5
        UnspecifiedValue = 6
        Cold = 7

    _battery_sn = db.Column('battery_sn',
                            db.Unicode,
                            primary_key=True)
    _num = db.Column('num',
                     db.SmallInteger,
                     primary_key=True)
    size = db.Column(db.Integer, nullable=False)
    voltage = db.Column(db.Integer, nullable=False)
    cycle_count = db.Column(db.Integer)
    health = db.Column(db.Enum(BatteryHealth))
    __table_args__ = (
        db.ForeignKeyConstraint(
            ['battery_sn', 'num'],
            ['battery.mobile_sn', 'battery.num'],
            ondelete='CASCADE'
        ),
    )

    def __init__(self, adb, props) -> None:
        super().__init__()
        # todo try if no size to not return this event
        try:
            size = get_prop(adb.dumpsys.splitlines(), 'Estimated battery capacity')  # mAh
        except IndexError:
            raise NoMeasure()

        size, *_ = size.split()
        self.size = int(size)
        self.cycle_count = get_prop(props, 'Charge counter', None)
        if self.cycle_count == 0:  # 0 is a wrong measure
            self.cycle_count = None
        self.voltage = get_prop(props, 'voltage')
        self.health = self.BatteryHealth(get_prop(props, 'health'))


class NoMeasure(Exception):
    pass


class Camera(InheritanceMixin, Component):
    class Facing(Enum):
        Front = 'Front'
        Back = 'Back'

        @classmethod
        def from_dumpsys(cls, value):
            return cls.Front if value.split(':')[1].strip() == 'FRONT' else cls.Back

    height = db.Column(db.Integer)
    width = db.Column(db.Integer)
    focal_length = db.Column(db.SmallInteger)
    video_height = db.Column(db.SmallInteger)
    video_width = db.Column(db.Integer)
    horizontal_view_angle = db.Column(db.Integer)
    facing = db.Column(db.Enum(Facing))
    vertical_view_angle = db.Column(db.SmallInteger)
    video_stabilization = db.Column(db.Boolean)
    flash = db.Column(db.Boolean)

    def __init__(self, model, manufacturer, height, width, focal_length, video_height, video_width,
                 horizontal_view_angle, facing, vertical_view_angle, video_stabilization,
                 flash) -> None:
        self.manufacturer = manufacturer
        self.model = model
        self.height = height
        self.width = width
        self.focal_length = focal_length
        self.video_height = video_height
        self.video_width = video_width
        self.horizontal_view_angle = horizontal_view_angle
        self.facing = facing
        self.vertical_view_angle = vertical_view_angle
        self.video_stabilization = video_stabilization
        self.flash = flash
        logging.debug('Camera %s', self)

    @classmethod
    def new(cls, adb: Adb):
        cameras = (l for l in adb.dumpsys.splitlines() if 'Camera ' in l and ' information:' in l)
        models = text.grep(adb.dumpsys, 'camera-name:')
        manufacturers = text.grep(adb.dumpsys, 'exif-make:')
        facings = text.grep(adb.dumpsys, 'Facing:')
        previews = text.grep(adb.dumpsys, 'preview-size-values:')
        videos = text.grep(adb.dumpsys, 'video-size-values:')
        pictures = text.grep(adb.dumpsys, 'picture-size-values:')
        focal_lengths = text.grep(adb.dumpsys, 'focal-length:')
        horizontal_view_angles = text.grep(adb.dumpsys, 'horizontal-view-angle:')
        vertical_view_angles = text.grep(adb.dumpsys, 'vertical-view-angle:')
        video_stabilizations = text.grep(adb.dumpsys, 'video-stabilization-supported:')
        flash_mode_values = text.grep(adb.dumpsys, 'flash-mode-values:')

        for _ in cameras:
            model = None
            with suppress(StopIteration):
                model = next(models).split(':')[1].strip()

            manufacturer = None
            with suppress(StopIteration):
                manufacturer = next(manufacturers).split(':')[1].strip()

            video = next(videos, next(previews))
            v_width, v_height, *_ = text.numbers(video)

            picture = next(pictures)
            p_width, p_height, *_ = text.numbers(picture)
            try:
                yield Camera(
                    model=model,
                    manufacturer=manufacturer,
                    width=p_width,
                    height=p_height,
                    video_height=v_height,
                    video_width=v_width,
                    focal_length=next(text.numbers(next(focal_lengths))),
                    horizontal_view_angle=next(text.numbers(next(horizontal_view_angles))),
                    vertical_view_angle=next(text.numbers(next(vertical_view_angles))),
                    facing=cls.Facing.from_dumpsys(next(facings)),
                    video_stabilization='true' in next(video_stabilizations),
                    flash='torch' in next(flash_mode_values, '')
                )
            except StopIteration as e:
                raise ValueError('Stopped iteration') from e


def get_prop(values, name: str, default: Any = -1):
    for line in values:
        try:
            n, value, *_ = line.strip().split(':')
        except ValueError:
            continue
        else:
            if name == n:
                return yaml.load(value.strip(), Loader=yaml.SafeLoader)
    if default == -1:
        raise IndexError('Value {} not found.'.format(name))
    else:
        return default


class NoDevice(Exception):
    pass
