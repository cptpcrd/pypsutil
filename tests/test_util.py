import math
import resource

import pytest

import pypsutil


def test_swap_info_percent() -> None:
    sinfo = pypsutil.SwapInfo(total=0, used=0, sin=0, sout=0)
    assert sinfo.free == 0
    assert sinfo.percent == 0.0

    sinfo = pypsutil.SwapInfo(total=100, used=0, sin=0, sout=0)
    assert sinfo.free == 100
    assert sinfo.percent == 0.0

    sinfo = pypsutil.SwapInfo(total=100, used=70, sin=0, sout=0)
    assert sinfo.free == 30
    assert sinfo.percent == 70.0


def test_battery_info() -> None:
    binfo = pypsutil.BatteryInfo(
        name="BAT0",
        status=pypsutil.BatteryStatus.FULL,
        percent=100.0,
        energy_full=None,
        energy_now=None,
        power_now=None,
    )

    assert binfo.power_plugged is None

    assert binfo.secsleft is not None
    assert binfo.secsleft > 0
    assert math.isinf(binfo.secsleft)

    assert binfo.secsleft_full == 0.0

    assert (
        str(binfo) == "BatteryInfo(name='BAT0', status=<BatteryStatus.FULL: 'full'>, "
        "power_plugged=None, percent=100.0, secsleft=inf, secsleft_full=0.0)"
    )

    binfo = pypsutil.BatteryInfo(
        name="BAT0",
        status=pypsutil.BatteryStatus.CHARGING,
        percent=90.0,
        energy_full=None,
        energy_now=None,
        power_now=None,
    )

    assert binfo.power_plugged is True

    assert binfo.secsleft is not None
    assert binfo.secsleft > 0
    assert math.isinf(binfo.secsleft)

    assert binfo.secsleft_full is None

    assert (
        str(binfo) == "BatteryInfo(name='BAT0', status=<BatteryStatus.CHARGING: 'charging'>, "
        "power_plugged=True, percent=90.0, secsleft=inf, secsleft_full=None)"
    )

    binfo = pypsutil.BatteryInfo(
        name="BAT0",
        status=pypsutil.BatteryStatus.CHARGING,
        percent=90.0,
        energy_full=100,
        energy_now=100,
        power_now=0,
    )

    assert binfo.power_plugged is True

    assert binfo.secsleft is not None
    assert binfo.secsleft > 0
    assert math.isinf(binfo.secsleft)

    assert binfo.secsleft_full is None

    assert (
        str(binfo) == "BatteryInfo(name='BAT0', status=<BatteryStatus.CHARGING: 'charging'>, "
        "power_plugged=True, percent=90.0, secsleft=inf, secsleft_full=None)"
    )

    binfo = pypsutil.BatteryInfo(
        name="BAT0",
        status=pypsutil.BatteryStatus.CHARGING,
        percent=90.0,
        energy_full=100,
        energy_now=90,
        power_now=10,
    )

    assert binfo.power_plugged is True

    assert binfo.secsleft is not None
    assert binfo.secsleft > 0
    assert math.isinf(binfo.secsleft)

    assert binfo.secsleft_full == 3600.0

    assert (
        str(binfo) == "BatteryInfo(name='BAT0', status=<BatteryStatus.CHARGING: 'charging'>, "
        "power_plugged=True, percent=90.0, secsleft=inf, secsleft_full=3600.0)"
    )

    binfo = pypsutil.BatteryInfo(
        name="BAT0",
        status=pypsutil.BatteryStatus.DISCHARGING,
        percent=90.0,
        energy_full=100,
        energy_now=90,
        power_now=10,
    )

    assert binfo.power_plugged is False
    assert binfo.secsleft == 3600 * 9
    assert binfo.secsleft_full is None

    assert (
        str(binfo) == "BatteryInfo(name='BAT0', status=<BatteryStatus.DISCHARGING: 'discharging'>, "
        "power_plugged=False, percent=90.0, secsleft=32400.0, secsleft_full=None)"
    )

    binfo = pypsutil.BatteryInfo(
        name="BAT0",
        status=pypsutil.BatteryStatus.DISCHARGING,
        percent=90.0,
        energy_full=100,
        energy_now=90,
        power_now=0,
    )

    assert binfo.power_plugged is False
    assert binfo.secsleft is None
    assert binfo.secsleft_full is None

    assert (
        str(binfo) == "BatteryInfo(name='BAT0', status=<BatteryStatus.DISCHARGING: 'discharging'>, "
        "power_plugged=False, percent=90.0, secsleft=None, secsleft_full=None)"
    )


def test_ps_sensor_info() -> None:
    bat_full = pypsutil.BatteryInfo(
        name="BAT0",
        status=pypsutil.BatteryStatus.FULL,
        percent=100.0,
        energy_full=None,
        energy_now=None,
        power_now=None,
    )

    bat_charging = pypsutil.BatteryInfo(
        name="BAT1",
        status=pypsutil.BatteryStatus.CHARGING,
        percent=90.0,
        energy_full=None,
        energy_now=None,
        power_now=None,
    )

    bat_discharging = pypsutil.BatteryInfo(
        name="BAT2",
        status=pypsutil.BatteryStatus.DISCHARGING,
        percent=90.0,
        energy_full=None,
        energy_now=None,
        power_now=None,
    )

    bat_unknown = pypsutil.BatteryInfo(
        name="BAT3",
        status=pypsutil.BatteryStatus.UNKNOWN,
        percent=90.0,
        energy_full=None,
        energy_now=None,
        power_now=None,
    )

    ac_online = pypsutil.ACPowerInfo(name="ADP1", is_online=True)
    ac_offline = pypsutil.ACPowerInfo(name="ADP2", is_online=False)

    psinfo = pypsutil.PowerSupplySensorInfo(batteries=[], ac_supplies=[])
    assert psinfo.is_on_ac_power is None

    psinfo = pypsutil.PowerSupplySensorInfo(batteries=[bat_full, bat_unknown], ac_supplies=[])
    assert psinfo.is_on_ac_power is None

    psinfo = pypsutil.PowerSupplySensorInfo(
        batteries=[bat_full, bat_unknown], ac_supplies=[ac_offline, ac_offline]
    )
    assert psinfo.is_on_ac_power is False

    psinfo = pypsutil.PowerSupplySensorInfo(
        batteries=[bat_full, bat_unknown], ac_supplies=[ac_online]
    )
    assert psinfo.is_on_ac_power is True

    psinfo = pypsutil.PowerSupplySensorInfo(
        batteries=[bat_full, bat_unknown], ac_supplies=[ac_offline, ac_online]
    )
    assert psinfo.is_on_ac_power is True

    psinfo = pypsutil.PowerSupplySensorInfo(batteries=[bat_charging], ac_supplies=[])
    assert psinfo.is_on_ac_power is True

    psinfo = pypsutil.PowerSupplySensorInfo(batteries=[bat_discharging], ac_supplies=[])
    assert psinfo.is_on_ac_power is False


def test_check_rlimit_resource() -> None:
    pypsutil._util.check_rlimit_resource(resource.RLIMIT_NOFILE)  # pylint: disable=protected-access

    with pytest.raises(ValueError, match=r"^invalid resource specified$"):
        pypsutil._util.check_rlimit_resource(  # pylint: disable=protected-access
            max(pypsutil._util.RESOURCE_NUMS) + 1  # pylint: disable=protected-access
        )
