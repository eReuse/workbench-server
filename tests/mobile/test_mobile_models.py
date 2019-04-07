from pathlib import Path
from unittest.mock import MagicMock

import bitmath
import pytest

from tests.mobile.conftest import _return_file_factory
from workbench_server.mobile.models import Camera, Mobile, SnapshotMobile


def test_galaxy_nexus(tmpdir, mocked_adb):
    mocked_adb.shell = MagicMock(side_effect=_return_file_factory('GalaxyNexus'))
    s = SnapshotMobile('1234')
    s.run(Path(tmpdir.strpath))
    m = s.device
    assert m.model == 'Galaxy Nexus'
    assert m.name == 'maguro'
    assert m.manufacturer == 'Samsung'
    assert m.imei == 351565050270559
    assert m.processor_model == 'Tuna'  # Not right although it seems it is android problem
    assert m.processor_cores == 2
    assert m.processor_board == 'tuna'
    assert m.processor_abi == 'armeabi-v7a'
    assert m.ram_size == 1020
    assert m.data_storage_size == 13644
    assert m.graphic_card_manufacturer == 'Imagination Technologies'
    assert m.graphic_card_model == 'PowerVR SGX 540'
    # assert m.macs == {'a0:0b:ba:cb:c9:f1', 'be:55:63:37:c5:cb',
    #                  'f6:7a:de:f4:0b:e2', 'a2:0b:ba:cb:c9:f1', 'a2:58:a8:43:31:35'}
    assert m.bluetooth_mac == '84:25:DB:9A:81:42'
    display = m.components[0]
    assert display.contrast_ratio is None  # todo
    assert display.density_height == 318
    assert display.density_width == 315
    assert display.refresh_rate == 60
    assert display.resolution_height == 1280
    assert display.resolution_width == 720
    assert display.size == 4.63
    assert display.technology is None  # todo
    assert display.touchable

    battery = m.components[1]
    assert battery.charge_counter == 0  # todo !
    assert battery.health == 2  # todo what does it mean?
    assert battery.size == 1750
    assert battery.status == 2  # todo is the same as health?
    assert battery.technology == 'Li-ion'  # todo normalize to dh enum
    assert battery.voltage == 3963
    assert not battery.wireless  # todo get a case of wireless battery

    camera1, camera2 = m.components[2:]
    assert camera1.focal_length == 3.43
    assert camera1.model == 'S5K4E1GA'
    assert camera1.video_width == 1920
    assert camera1.video_height == 1080
    assert camera1.height == 1960
    assert camera1.width == 2608
    assert camera1.facing == Camera.Facing.Back
    assert camera1.manufacturer == 'Samsung'
    assert camera1.flash
    assert camera1.horizontal_view_angle == 54.8
    assert camera1.vertical_view_angle == 42.5

    assert camera1.video_stabilization
    assert camera2.focal_length == 1.95
    assert camera2.model == 'S5K6A1GX03'
    assert camera2.video_width == 1280
    assert camera2.video_height == 720
    assert camera2.height == 1024
    assert camera2.width == 1280
    assert camera2.facing == Camera.Facing.Front
    assert not camera2.flash
    assert camera2.horizontal_view_angle == 54.8
    assert camera2.vertical_view_angle == 42.5
    assert camera2.video_stabilization


def test_nexus_7(tmpdir, mocked_adb: MagicMock):
    mocked_adb.shell = MagicMock(side_effect=_return_file_factory('Nexus7'))
    s = SnapshotMobile('1234')
    s.run(Path(tmpdir.strpath))
    m = s.device
    assert m.model == 'Nexus 7'
    assert m.name == 'razor'
    assert m.manufacturer == 'asus'
    assert not m.imei
    assert m.processor_model == 'QCT APQ8064 FLO'
    assert m.processor_cores == 4
    assert m.processor_board == 'flo'
    assert m.processor_abi == 'armeabi-v7a'
    assert m.ram_size == 1849
    assert m.data_storage_size == 12828
    assert m.graphic_card_manufacturer == 'Qualcomm'
    assert m.graphic_card_model == 'Adreno (TM) 320'
    # assert m.macs == {'14:dd:a9:44:7e:d9', '16:dd:a9:44:7e:d9'}
    assert m.bluetooth_mac == '14:DD:A9:44:7E:D8'
    display = m.components[0]
    assert display.contrast_ratio is None  # todo
    assert display.density_height == 322
    assert display.density_width == 320
    assert display.refresh_rate == 60
    assert display.resolution_height == 1920
    assert display.resolution_width == 1200
    assert display.size == 7.04
    assert display.technology is None  # todo
    assert display.touchable

    battery = m.components[1]
    assert battery.charge_counter == 0  # todo !
    assert battery.health == 2  # todo what does it mean?
    assert battery.size == 3448
    assert battery.status == 2  # todo is the same as health?
    assert battery.technology == 'Li-ion'  # todo normalize to dh enum
    assert battery.voltage == 3904
    assert not battery.wireless  # todo get a case of wireless battery

    camera1, camera2 = m.components[2:]
    assert camera1.focal_length == 2.95
    assert not camera1.model
    assert camera1.video_width == 1920
    assert camera1.video_height == 1080
    assert camera1.height == 1944
    assert camera1.width == 2592
    assert camera1.facing == Camera.Facing.Back
    assert not camera1.manufacturer
    assert not camera1.flash
    assert camera1.horizontal_view_angle == 180
    assert camera1.vertical_view_angle == 180
    assert not camera1.video_stabilization

    assert camera2.focal_length == 4.6
    assert not camera2.model
    assert camera2.video_width == 1280
    assert camera2.video_height == 768
    assert camera2.height == 768
    assert camera2.width == 1280
    assert camera2.facing == Camera.Facing.Front
    assert not camera2.flash
    assert camera2.horizontal_view_angle == 180
    assert camera2.vertical_view_angle == 180
    assert not camera2.video_stabilization


def test_smt110(tmpdir, mocked_adb: MagicMock):
    mocked_adb.shell = MagicMock(side_effect=_return_file_factory('SM-T110'))
    s = SnapshotMobile('1234')
    s.run(Path(tmpdir.strpath))
    m = s.device
    x = 1


def test_gti9195(tmpdir, mocked_adb: MagicMock):
    mocked_adb.shell = MagicMock(side_effect=_return_file_factory('GT-I9195'))
    s = SnapshotMobile('1234')
    s.run(Path(tmpdir.strpath))
    m = s.device


def test_sma300fu(tmpdir, mocked_adb: MagicMock):
    mocked_adb.shell = MagicMock(side_effect=_return_file_factory('SM-A300FU'))
    s = SnapshotMobile('1234')
    s.run(Path(tmpdir.strpath))
    m = s.device


def test_oneplus_a5000(tmpdir, mocked_adb: MagicMock):
    mocked_adb.shell = MagicMock(side_effect=_return_file_factory('ONEPLUSA5000'))
    s = SnapshotMobile('1234')
    s.run(Path(tmpdir.strpath))
    m = s.device


@pytest.mark.xfail(reason='phone has gpu but not in dumpsys?')
def test_htc_desire_s(tmpdir, mocked_adb: MagicMock):
    mocked_adb.shell = MagicMock(side_effect=_return_file_factory('HTCDesireS'))
    s = SnapshotMobile('1234')
    s.run(Path(tmpdir.strpath))
    m = s.device
