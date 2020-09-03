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
                                "current_now": "350",
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
        batteries, mains = pypsutil.sensors_power()  # type: ignore

        assert batteries == [
            pypsutil.BatteryInfo(  # type: ignore
                name="BAT0",
                percent=100.0,
                secsleft=float("inf"),
                secsleft_full=0,
                power_plugged=True,
            ),
            pypsutil.BatteryInfo(  # type: ignore
                name="BAT1",
                percent=89.9,
                secsleft=float("inf"),
                secsleft_full=None,
                power_plugged=True,
            ),
            pypsutil.BatteryInfo(  # type: ignore
                name="BAT2",
                percent=70,
                secsleft=7200,
                secsleft_full=None,
                power_plugged=False,
            ),
            pypsutil.BatteryInfo(  # type: ignore
                name="BAT3",
                percent=70,
                secsleft=float("inf"),
                secsleft_full=3600,
                power_plugged=True,
            ),
            pypsutil.BatteryInfo(  # type: ignore
                name="BAT4",
                percent=70,
                secsleft=7200,
                secsleft_full=None,
                power_plugged=False,
            ),
            pypsutil.BatteryInfo(  # type: ignore
                name="BAT5",
                percent=70,
                secsleft=None,
                secsleft_full=None,
                power_plugged=None,
            ),
            pypsutil.BatteryInfo(  # type: ignore
                name="BAT6",
                percent=70,
                secsleft=float("inf"),
                secsleft_full=3600,
                power_plugged=True,
            ),
        ]

        assert mains == [
            pypsutil.ACPowerInfo(name="AC0", is_online=True),  # type: ignore
            pypsutil.ACPowerInfo(name="AC1", is_online=False),  # type: ignore
        ]

        assert pypsutil.sensors_is_on_ac_power() is True  # type: ignore


@pytest.mark.skipif(sys.platform != "linux", reason="Tests Linux-specific behavior")  # type: ignore
def test_sensors_battery(tmp_path: pathlib.Path) -> None:
    def test_info(
        ps_info: Dict[str, Dict[str, str]],
        battery_info: Optional[pypsutil.BatteryInfo],  # type: ignore
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
                    "charge_now": "10000",
                    "charge_full": "10000",
                },
                "AC0": {
                    "type": "Mains\n",
                    "online": "1",
                },
            },
            pypsutil.BatteryInfo(  # type: ignore
                name="BAT0",
                percent=100,
                secsleft=float("inf"),
                secsleft_full=0,
                power_plugged=True,
            ),
        )

        test_info(
            {
                "BAT0": {
                    "type": "Battery\n",
                    "status": "unknown",
                    "current_now": "100",
                    "charge_now": "10000",
                    "charge_full": "10000",
                },
            },
            pypsutil.BatteryInfo(  # type: ignore
                name="BAT0",
                percent=100,
                secsleft=None,
                secsleft_full=None,
                power_plugged=None,
            ),
        )

        test_info(
            {
                "BAT0": {
                    "type": "Battery\n",
                    "status": "unknown",
                    "current_now": "100",
                    "charge_now": "10000",
                    "charge_full": "10000",
                },
                "AC0": {
                    "type": "Mains\n",
                    "online": "1",
                },
            },
            pypsutil.BatteryInfo(  # type: ignore
                name="BAT0",
                percent=100,
                secsleft=float("inf"),
                secsleft_full=None,
                power_plugged=True,
            ),
        )

        test_info(
            {
                "BAT0": {
                    "type": "Battery\n",
                    "status": "unknown",
                    "current_now": "100",
                    "charge_now": "10000",
                    "charge_full": "10000",
                },
                "AC0": {
                    "type": "Mains\n",
                    "online": "0",
                },
            },
            pypsutil.BatteryInfo(  # type: ignore
                name="BAT0",
                percent=100,
                secsleft=None,
                secsleft_full=None,
                power_plugged=False,
            ),
        )

        test_info(
            {
                "BAT0": {
                    "type": "Battery\n",
                    "status": "discharging",
                    "charge_now": "10000",
                    "charge_full": "10000",
                },
            },
            pypsutil.BatteryInfo(  # type: ignore
                name="BAT0",
                percent=100,
                secsleft=None,
                secsleft_full=None,
                power_plugged=False,
            ),
        )

        test_info(
            {
                "BAT0": {
                    "type": "Battery\n",
                    "status": "charging",
                    "charge_now": "10000",
                    "charge_full": "10000",
                },
            },
            pypsutil.BatteryInfo(  # type: ignore
                name="BAT0",
                percent=100,
                secsleft=float("inf"),
                secsleft_full=None,
                power_plugged=True,
            ),
        )


@pytest.mark.skipif(sys.platform != "linux", reason="Tests Linux-specific behavior")  # type: ignore
def test_sensors_power_empty(tmp_path: pathlib.Path) -> None:
    with replace_info_directories(sysfs=str(tmp_path)):
        assert pypsutil.sensors_power() == ([], [])  # type: ignore

        assert pypsutil.sensors_battery() is None  # type: ignore

        assert pypsutil.sensors_is_on_ac_power() is None  # type: ignore
