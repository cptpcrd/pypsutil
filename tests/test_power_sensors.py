# pylint: disable=no-member
import pathlib
import shutil
import sys
from typing import Dict, Optional

import pytest

import pypsutil

from .util import populate_directory, replace_info_directories


def build_supply_uevent(data: Dict[str, str]) -> str:
    return "".join("POWER_SUPPLY_{}={}\n".format(key.upper(), value) for key, value in data.items())


@pytest.mark.skipif(sys.platform != "linux", reason="Tests Linux-specific behavior")  # type: ignore
def test_sensors_power(tmp_path: pathlib.Path) -> None:
    populate_directory(
        str(tmp_path),
        {
            "class": {
                "power_supply": {
                    "BAT0": {
                        "type": "Battery\n",
                        "status": "full",
                        "capacity": "100",
                        "charge_now": "10000",
                        "charge_full": "10000",
                    },
                    "BAT1": {
                        "type": "Battery\n",
                        "uevent": build_supply_uevent(
                            {
                                "status": "Charging",
                                "capacity": "90",
                                "energy_now": "899",
                                "energy_full": "1000",
                            }
                        ),
                    },
                    "BAT2": {
                        "type": "Battery\n",
                        "uevent": build_supply_uevent(
                            {
                                "status": "Discharging",
                                "capacity": "70",
                                "charge_now": "700",
                                "charge_full": "1000",
                                "current_now": "350",
                                "voltage_now": "2000000",
                            }
                        ),
                    },
                    "BAT3": {
                        "type": "Battery\n",
                        "uevent": build_supply_uevent(
                            {
                                "status": "Charging",
                                "capacity": "70",
                                "energy_now": "700",
                                "energy_full": "1000",
                                "power_now": "300",
                            }
                        ),
                    },
                    "BAT4": {
                        "type": "Battery\n",
                        "status": "Discharging",
                        "energy_now": "700",
                        "energy_full": "1000",
                        "power_now": "350",
                    },
                    "BAT5": {
                        "type": "Battery\n",
                        "status": "Unknown",
                        "energy_now": "700",
                        "energy_full": "1000",
                        "power_now": "350",
                    },
                    "BAT6": {
                        "type": "Battery\n",
                        "status": "Charging",
                        "charge_now": "700",
                        "charge_full": "1000",
                        "current_now": "300",
                        "voltage_now": "1000000",
                    },
                    # Will be ignored for lack of information
                    "BAT7": {
                        "type": "Battery\n",
                        "status": "Charging",
                    },
                    "AC0": {
                        "type": "Mains\n",
                        "online": "1",
                    },
                    "AC1": {
                        # The "online=1" line should be ignored
                        "uevent": "POWER_SUPPLY_TYPE=Mains\nPOWER_SUPPLY_ONLINE=0\nonline=1\n",
                    },
                    # Will be ignored for lack of information
                    "AC2": {
                        "type": "Mains\n",
                    },
                },
            },
        },
    )

    with replace_info_directories(sysfs=str(tmp_path)):
        psinfo = pypsutil.sensors_power()  # type: ignore

        assert psinfo.batteries == [
            pypsutil.BatteryInfo(
                name="BAT0",
                percent=100.0,
                status=pypsutil.BatteryStatus.FULL,
                energy_now=None,
                energy_full=None,
                power_now=None,
            ),
            pypsutil.BatteryInfo(
                name="BAT1",
                percent=89.9,
                status=pypsutil.BatteryStatus.CHARGING,
                energy_now=899,
                energy_full=1000,
                power_now=None,
            ),
            pypsutil.BatteryInfo(
                name="BAT2",
                percent=70,
                status=pypsutil.BatteryStatus.DISCHARGING,
                energy_now=1400,
                energy_full=2000,
                power_now=700,
            ),
            pypsutil.BatteryInfo(
                name="BAT3",
                percent=70,
                status=pypsutil.BatteryStatus.CHARGING,
                energy_now=700,
                energy_full=1000,
                power_now=300,
            ),
            pypsutil.BatteryInfo(
                name="BAT4",
                percent=70,
                status=pypsutil.BatteryStatus.DISCHARGING,
                energy_now=700,
                energy_full=1000,
                power_now=350,
            ),
            pypsutil.BatteryInfo(
                name="BAT5",
                percent=70,
                status=pypsutil.BatteryStatus.UNKNOWN,
                energy_now=700,
                energy_full=1000,
                power_now=350,
            ),
            pypsutil.BatteryInfo(
                name="BAT6",
                percent=70,
                status=pypsutil.BatteryStatus.CHARGING,
                energy_now=700,
                energy_full=1000,
                power_now=300,
            ),
        ]

        assert pypsutil.sensors_battery_total() == pypsutil.BatteryInfo(  # type: ignore
            name="Combined",
            percent=5099 * 100 / 7000,
            status=pypsutil.BatteryStatus.UNKNOWN,
            energy_now=5099,
            energy_full=7000,
            power_now=None,
            _power_plugged=True,
        )

        assert psinfo.ac_supplies == [
            pypsutil.ACPowerInfo(name="AC0", is_online=True),
            pypsutil.ACPowerInfo(name="AC1", is_online=False),
        ]

        assert pypsutil.sensors_is_on_ac_power() is True  # type: ignore


@pytest.mark.skipif(sys.platform != "linux", reason="Tests Linux-specific behavior")  # type: ignore
def test_sensors_battery(tmp_path: pathlib.Path) -> None:
    def test_info(
        ps_info: Dict[str, Dict[str, str]],
        battery_info: Optional[pypsutil.BatteryInfo],
    ) -> None:
        populate_directory(str(tmp_path), {"class": {"power_supply": ps_info}})

        assert pypsutil.sensors_battery() == battery_info  # type: ignore

        shutil.rmtree(tmp_path / "class")

    with replace_info_directories(sysfs=str(tmp_path)):
        test_info(
            {
                "BAT0": {
                    "type": "Battery\n",
                    "status": "full",
                    "capacity": "100",
                    "charge_now": "10000",
                    "charge_full": "10000",
                },
                "AC0": {
                    "type": "Mains\n",
                    "online": "1",
                },
            },
            pypsutil.BatteryInfo(
                name="BAT0",
                percent=100,
                energy_now=None,
                energy_full=None,
                power_now=None,
                status=pypsutil.BatteryStatus.FULL,
                _power_plugged=True,
            ),
        )

        test_info(
            {
                "BAT0": {
                    "type": "Battery\n",
                    "status": "unknown",
                    "power_now": "100",
                    "energy_now": "10000",
                    "energy_full": "10000",
                },
            },
            pypsutil.BatteryInfo(
                name="BAT0",
                percent=100,
                power_now=100,
                energy_now=10000,
                energy_full=10000,
                status=pypsutil.BatteryStatus.UNKNOWN,
                _power_plugged=None,
            ),
        )

        test_info(
            {
                "BAT0": {
                    "type": "Battery\n",
                    "status": "unknown",
                    "power_now": "100",
                    "energy_now": "10000",
                    "energy_full": "10000",
                },
                "AC0": {
                    "type": "Mains\n",
                    "online": "1",
                },
            },
            pypsutil.BatteryInfo(
                name="BAT0",
                percent=100,
                power_now=100,
                energy_now=10000,
                energy_full=10000,
                status=pypsutil.BatteryStatus.UNKNOWN,
                _power_plugged=True,
            ),
        )

        test_info(
            {
                "BAT0": {
                    "type": "Battery\n",
                    "status": "unknown",
                    "power_now": "100",
                    "energy_now": "10000",
                    "energy_full": "10000",
                },
                "AC0": {
                    "type": "Mains\n",
                    "online": "0",
                },
            },
            pypsutil.BatteryInfo(
                name="BAT0",
                percent=100,
                power_now=100,
                energy_now=10000,
                energy_full=10000,
                status=pypsutil.BatteryStatus.UNKNOWN,
                _power_plugged=False,
            ),
        )

        test_info(
            {
                "BAT0": {
                    "type": "Battery\n",
                    "status": "discharging",
                    "energy_now": "10000",
                    "energy_full": "10000",
                },
            },
            pypsutil.BatteryInfo(
                name="BAT0",
                percent=100,
                power_now=None,
                energy_now=10000,
                energy_full=10000,
                status=pypsutil.BatteryStatus.DISCHARGING,
            ),
        )

        test_info(
            {
                "BAT0": {
                    "type": "Battery\n",
                    "status": "charging",
                    "energy_now": "10000",
                    "energy_full": "10000",
                },
            },
            pypsutil.BatteryInfo(
                name="BAT0",
                percent=100,
                power_now=None,
                energy_now=10000,
                energy_full=10000,
                status=pypsutil.BatteryStatus.CHARGING,
            ),
        )


@pytest.mark.skipif(sys.platform != "linux", reason="Tests Linux-specific behavior")  # type: ignore
def test_sensors_is_on_ac_power(tmp_path: pathlib.Path) -> None:
    def test_info(
        ps_info: Dict[str, Dict[str, str]],
        ac_power_result: Optional[bool],
    ) -> None:
        populate_directory(str(tmp_path), {"class": {"power_supply": ps_info}})

        assert pypsutil.sensors_is_on_ac_power() == ac_power_result  # type: ignore

        shutil.rmtree(tmp_path / "class")

    with replace_info_directories(sysfs=str(tmp_path)):
        test_info(
            {
                "BAT0": {
                    "type": "Battery\n",
                    "status": "full",
                    "voltage_now": "1000000",
                    "charge_now": "10000",
                    "charge_full": "10000",
                },
                "AC0": {
                    "type": "Mains\n",
                    "online": "1",
                },
            },
            True,
        )

        test_info(
            {
                "BAT0": {
                    "type": "Battery\n",
                    "status": "unknown",
                    "voltage_now": "1000000",
                    "current_now": "100",
                    "charge_now": "10000",
                    "charge_full": "10000",
                },
            },
            None,
        )

        test_info(
            {
                "BAT0": {
                    "type": "Battery\n",
                    "status": "unknown",
                    "capacity": "90",
                },
                "AC0": {
                    "type": "Mains\n",
                    "online": "1",
                },
            },
            True,
        )

        test_info(
            {
                "BAT0": {
                    "type": "Battery\n",
                    "status": "unknown",
                    "capacity": "90",
                },
                "AC0": {
                    "type": "Mains\n",
                    "online": "0",
                },
            },
            False,
        )

        test_info(
            {
                "BAT0": {
                    "type": "Battery\n",
                    "status": "discharging",
                    "capacity": "90",
                },
            },
            False,
        )

        test_info(
            {
                "BAT0": {
                    "type": "Battery\n",
                    "status": "charging",
                    "capacity": "90",
                },
            },
            True,
        )


@pytest.mark.skipif(sys.platform != "linux", reason="Tests Linux-specific behavior")  # type: ignore
def test_sensors_power_empty(tmp_path: pathlib.Path) -> None:
    with replace_info_directories(sysfs=str(tmp_path)):
        assert pypsutil.sensors_power() == pypsutil.PowerSupplySensorInfo(  # type: ignore
            batteries=[], ac_supplies=[]
        )

        assert pypsutil.sensors_battery() is None  # type: ignore

        assert pypsutil.sensors_is_on_ac_power() is None  # type: ignore
