import datetime
import json
import logging
import math
import pathlib
import uuid
from contextlib import suppress
from enum import Enum
from typing import Any

import bitmath
import yaml
from ereuse_utils import Dumpeable, cmd, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy.orm.exc import NoResultFound

from workbench_server.db import db
from workbench_server.models import Phases, Snapshot, SnapshotInheritorMixin


class Adb:
    def __init__(self, serial_number: str) -> None:
        self.serial_number = serial_number
        self.sh = 'adb', '-s', self.serial_number, 'shell'
        self.dumpsys = self.shell('dumpsys')

    def shell(self, *params, **kwargs) -> str:
        out = cmd.run(*self.sh, *params, **kwargs).stdout  # type: str
        return out.strip().replace('\t', '')

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
        device = json.loads(self.device.to_json())  # type: dict todo not nice
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

    def __init__(self, serial_number: str):
        super().__init__(device=Mobile(serial_number=serial_number),
                         phase=Phases.Info,
                         uuid=uuid.uuid4())

    def run(self, jsons: pathlib.Path):
        self.device.run()
        self.closed = datetime.datetime.now()
        self.phase = Phases.ReadyToUpload
        self.write(jsons)

    def __repr__(self) -> str:
        return '<Snapshot {0.uuid} Mobile {0.device}> '.format(self)


class Mobile(db.Model, Dumpeable):
    # Device fields
    serial_number = db.Column(db.Unicode, primary_key=True)
    model = db.Column(db.Unicode)
    name = db.Column(db.Unicode)
    manufacturer = db.Column(db.Unicode)
    # Mobile fields
    imei = db.Column(db.Integer)
    processor_model = db.Column(db.Unicode)
    processor_cores = db.Column(db.Integer)
    processor_board = db.Column(db.Unicode)
    processor_abi = db.Column(db.Unicode)
    ram_size = db.Column(db.Integer)
    data_storage_size = db.Column(db.Integer)
    graphic_card_manufacturer = db.Column(db.Unicode)
    graphic_card_model = db.Column(db.Unicode)
    macs = db.Column(postgresql.ARRAY(db.Unicode))
    bluetooth_mac = db.Column(db.Unicode)
    components = db.relationship('Component',
                                 cascade='all, delete-orphan',
                                 order_by=lambda: Component.num,
                                 collection_class=ordering_list('num'))
    snapshot_id = db.Column(postgresql.UUID(as_uuid=True),
                            db.ForeignKey(SnapshotMobile.uuid, ondelete='CASCADE'),
                            unique=True)

    @classmethod
    def get(cls, serial_number: str):
        return cls.query.filter_by(serial_number=serial_number).one()

    def run(self):
        self._adb = Adb(self.serial_number)
        props = self._get_properties()

        self.model = get_prop(props, 'ro.product.model')
        self.name = get_prop(props,
                             'ro.product.subdevice',
                             get_prop(props, 'ro.product.name', None))
        self.manufacturer = get_prop(props, 'ro.product.manufacturer')
        self.imei = None
        with suppress(NoImei):
            self.imei = self._imei()

        self.closed = False
        self.events = []

        # Android does not report much info
        # We assume a SOC soldered in the phone

        # Processor
        cpuinfo = self._adb.shell('cat', '/proc/cpuinfo').splitlines()
        self.processor_model = get_prop(cpuinfo, 'Hardware')
        self.processor_cores = len(
            tuple(text.numbers(self._adb.shell('ls', '/sys/devices/system/cpu'))))
        self.processor_board = get_prop(props, 'ro.product.board')
        self.processor_abi = get_prop(props, 'ro.product.cpu.abi')

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

        # Graphic card
        gpu = next(text.grep(self._adb.dumpsys, 'GLES:'))
        self.graphic_card_manufacturer, self.graphic_card_model, *_ = gpu.split(':')[1].split(', ')
        self.graphic_card_manufacturer = self.graphic_card_manufacturer.strip()
        self.graphic_card_model = self.graphic_card_model.strip()

        logging.debug('Graphic Card for %s', self)

        # Network macs
        self.macs = set(
            text.macs(' '.join(text.grep(self._adb.shell('ip', 'addr', 'show'), 'link/ether')))
        )
        self.macs.discard('ff:ff:ff:ff:ff:ff')
        self.bluetooth_mac = self._adb.shell('settings', 'get', 'secure', 'bluetooth_address')

        logging.debug('Specs for %s', self)

        self.components.append(Display(self._adb))
        self.components.append(Battery(self._adb))
        self.components.extend(Camera.new(self._adb))

    def _get_properties(self) -> list:
        return self._adb.shell('getprop').replace('[', '').replace(']', '').splitlines()

    def _imei(self):
        # https://stackoverflow.com/questions/6852106/is-there-an-android-shell-or-adb-command-that-i-could-use-to-get-a-devices-imei/37940140#37940140
        cmd = 'adb', 'shell', 'service', 'call', 'iphonesubinfo'
        imei = self._adb.shell(*cmd, 1)
        if not imei:
            imei = self._adb.shell(*cmd, 16)
        try:
            _, i0, _, i1, _, i2, *_ = imei.split('\'')
            imei = i0 + i1 + i2
            imei = imei.replace('.', '').strip()
            return int(imei)
        except ValueError:
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


class NoImei(Exception):
    pass


class Component(db.Model, Dumpeable):
    mobile_sn = db.Column(db.Unicode,
                          db.ForeignKey(Mobile.serial_number, ondelete='CASCADE'),
                          primary_key=True)
    num = db.Column(db.SmallInteger, primary_key=True)
    type = db.Column(db.Unicode, nullable=False, index=True)

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
            args['inherit_condition'] = (cls.mobile_sn == Component.mobile_sn) & \
                                        (cls.num == Component.num)
        return args

    def __repr__(self) -> str:
        return '<Component {0.num}: {0.__class__.__name__}>'.format(self)


class InheritanceMixin:
    @declared_attr
    def mobile_sn(cls):
        return db.Column(db.Unicode, primary_key=True)

    @declared_attr
    def num(cls):
        return db.Column(db.SmallInteger, primary_key=True)

    @declared_attr
    def __table__args(cls):
        return (
            db.ForeignKeyConstraint(
                ['mobile_sn', 'num'],
                ['component.mobile_sn', 'component.num'],
                ondelete='CASCADE'
            ),
        )


class Display(InheritanceMixin, Component):
    resolution_width = db.Column(db.SmallInteger)
    resolution_height = db.Column(db.SmallInteger)
    refresh_rate = db.Column(db.SmallInteger)
    density_width = db.Column(db.SmallInteger)
    density_height = db.Column(db.SmallInteger)
    size = db.Column(db.Float(decimal_return_scale=2))
    touchable = db.Column(db.Boolean)
    technology = db.Column(db.Unicode)
    contrast_ratio = db.Column(db.Float(decimal_return_scale=3))

    def __init__(self, adb: Adb) -> None:
        display_info = next(text.grep(adb.dumpsys, 'PhysicalDisplayInfo'))
        self.resolution_width, self.resolution_height, self.refresh_rate, _internal_density, \
        self.density_width, self.density_height, *_ = text.numbers(display_info)

        self.density_width = int(self.density_width)
        self.density_height = int(self.density_height)
        self.refresh_rate = int(self.refresh_rate)

        self.size = round(math.sqrt(
            (self.resolution_width / self.density_width) ** _internal_density +
            (self.resolution_height / self.density_height) ** _internal_density
        ), ndigits=2)
        """Size. From https://stackoverflow.com/a/19446138/2710757."""
        self.technology = None
        self.contrast_ratio = None
        self.touchable = True
        logging.debug('Display %s', self)


class Battery(InheritanceMixin, Component):
    wireless = db.Column(db.Boolean)
    health = db.Column(db.SmallInteger)
    status = db.Column(db.SmallInteger)
    voltage = db.Column(db.Integer)
    technology = db.Column(db.Unicode)
    charge_counter = db.Column(db.Integer)
    size = db.Column(db.Integer)

    def __init__(self, adb: Adb) -> None:
        props = adb.shell('dumpsys', 'battery').splitlines()
        self.wireless = get_prop(props, 'Wireless powered')
        self.status = get_prop(props, 'status')
        self.health = get_prop(props, 'health')
        self.voltage = get_prop(props, 'voltage')
        self.technology = get_prop(props, 'technology')
        self.charge_counter = get_prop(props, 'Charge counter', None)
        self.size = get_prop(adb.dumpsys.splitlines(), 'Estimated battery capacity', None)  # mAh
        if self.size:
            self.size, *_ = self.size.split()
            self.size = int(self.size)
        logging.debug('Battery %s', self)


class Camera(InheritanceMixin, Component):
    class Facing(Enum):
        Front = 'Front'
        Back = 'Back'

        @classmethod
        def from_dumpsys(cls, value):
            return cls.Front if value.split(':')[1].strip() == 'FRONT' else cls.Back

    manufacturer = db.Column(db.Unicode)
    model = db.Column(db.Unicode)
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
    if name == 'voltage':
        x = 1
    for line in values:
        try:
            n, value, *_ = line.strip().split(':')
        except ValueError:
            continue
        else:
            if name == n:
                return yaml.load(value.strip())
    if default == -1:
        raise IndexError('Value {} not found.'.format(name))
    else:
        return default


class NoDevice(Exception):
    pass
