from pathlib import Path
from unittest.mock import MagicMock

import pytest

from workbench_server.mobile.models import Battery, Camera, Display, GraphicCard, MeasureBattery, \
    Processor, SnapshotMobile


def test_galaxy_nexus(tmpdir, mocked_adb):
    mocked_adb.set('GalaxyNexus')
    s = SnapshotMobile('1234')
    s.run(Path(tmpdir.strpath))
    m = s.device
    assert m.model == 'Galaxy Nexus'
    assert m.variant == 'maguro'
    assert m.manufacturer == 'Samsung'

    assert m.imei == 351565050270559
    assert m.ram_size == 1016
    assert m.data_storage_size == 13644

    cpu = m.components[0]
    assert isinstance(cpu, Processor)
    assert cpu.cores == 2
    assert cpu.model == 'Tuna'
    assert cpu.abi == 'armeabi-v7a'

    gpu = m.components[1]
    assert isinstance(gpu, GraphicCard)
    assert gpu.model == 'PowerVR SGX 540'
    assert gpu.manufacturer == 'Imagination Technologies'

    display = m.components[2]
    assert isinstance(display, Display)
    assert display.refresh_rate == 60
    assert display.resolution_height == 1280
    assert display.resolution_width == 720
    assert display.size == 4.63
    assert display.touchable

    battery = m.components[3]
    assert isinstance(battery, Battery)
    assert battery.size == 1750
    assert battery.technology == 'Li-ion'  # todo normalize to dh enum
    assert not battery.wireless

    measure_battery = next(iter(battery.events))
    assert isinstance(measure_battery, MeasureBattery)
    assert measure_battery.size == 1750
    assert measure_battery.cycle_count is None
    assert measure_battery.health == MeasureBattery.BatteryHealth.Good
    assert measure_battery.voltage == 3708

    camera1, camera2 = m.components[4:]
    assert isinstance(camera1, Camera)
    assert isinstance(camera2, Camera)
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

    assert s.data


def test_nexus_7(tmpdir, mocked_adb: MagicMock):
    mocked_adb.set('Nexus7')
    s = SnapshotMobile('1234')
    s.run(Path(tmpdir.strpath))
    m = s.device
    assert m.model == 'Nexus 7'
    assert m.variant == 'flo'
    assert m.manufacturer == 'asus'

    assert not m.imei
    assert m.ram_size == 1849
    assert m.data_storage_size == 12828

    cpu = m.components[0]
    assert isinstance(cpu, Processor)
    assert cpu.model == 'QCT APQ8064 FLO'
    assert cpu.cores == 4
    assert cpu.abi == 'armeabi-v7a'

    gpu = m.components[1]
    assert isinstance(gpu, GraphicCard)
    assert gpu.model == 'Adreno (TM) 320'
    assert gpu.manufacturer == 'Qualcomm'

    display = m.components[2]
    assert isinstance(display, Display)

    assert display.refresh_rate == 60
    assert display.resolution_height == 1920
    assert display.resolution_width == 1200
    assert display.size == 7.04
    assert display.touchable

    battery = m.components[3]
    assert isinstance(battery, Battery)
    assert battery.size == 3448
    assert battery.technology == 'Li-ion'
    assert not battery.wireless

    measure_battery = next(iter(battery.events))
    assert isinstance(measure_battery, MeasureBattery)
    assert measure_battery.size == 3448
    assert measure_battery.voltage == 4250
    assert measure_battery.cycle_count is None
    assert measure_battery.health == MeasureBattery.BatteryHealth.Good

    camera1, camera2 = m.components[4:]
    assert isinstance(camera1, Camera)
    assert isinstance(camera2, Camera)
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

    assert s.data


def test_smt110(tmpdir, mocked_adb: MagicMock):
    mocked_adb.set('SM-T110')
    s = SnapshotMobile('1234')
    s.run(Path(tmpdir.strpath))
    m = s.device
    assert s.data


def test_gti9195(tmpdir, mocked_adb: MagicMock):
    mocked_adb.set('GT-I9195')
    s = SnapshotMobile('1234')
    s.run(Path(tmpdir.strpath))
    m = s.device
    assert s.data


def test_sma300fu(tmpdir, mocked_adb: MagicMock):
    mocked_adb.set('SM-A300FU')
    s = SnapshotMobile('1234')
    s.run(Path(tmpdir.strpath))
    m = s.device
    assert s.data


def test_oneplus_a5000(tmpdir, mocked_adb: MagicMock):
    mocked_adb.set('ONEPLUSA5000')
    s = SnapshotMobile('1234')
    s.run(Path(tmpdir.strpath))
    m = s.device
    assert s.data


@pytest.mark.xfail(reason='phone has gpu but not in dumpsys?')
def test_htc_desire_s(tmpdir, mocked_adb: MagicMock):
    mocked_adb.set('HTCDesireS')
    s = SnapshotMobile('1234')
    s.run(Path(tmpdir.strpath))
    m = s.device
    assert s.data
