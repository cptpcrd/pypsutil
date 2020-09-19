# pylint: disable=no-member
import pathlib
import shutil

import pypsutil

from .util import linux_only, populate_directory, replace_info_directories


@linux_only  # type: ignore
def test_sensors_temperature(tmp_path: pathlib.Path) -> None:
    populate_directory(
        str(tmp_path),
        {
            "class": {
                "hwmon": {
                    "hwmon0": {
                        "name": "acpi",
                        "temp1_input": "50000\n",
                        "temp2_label": "BAD\n",
                    },
                    "hwmon1": {
                        "name": "acpi2",
                    },
                    "hwmon2": {
                        "name": "coretemp",
                        "temp1_input": "60000\n",
                        "temp1_max": "100000\n",
                        "temp1_crit": "100000\n",
                        "temp2_input": "90000\n",
                        "temp2_label": "Chassis\n",
                    },
                    "hwmon3": {
                        "name": "coretemp2",
                        "temp1_input": "60000",
                        "temp1_max": "100000",
                        "temp1_crit": "100000",
                        "temp2_input": "90000",
                        "temp2_label": "Chassis",
                    },
                },
            }
        },
    )

    with replace_info_directories(sysfs=str(tmp_path)):
        assert pypsutil.sensors_temperatures() == {  # type: ignore
            "acpi": [
                pypsutil.TempSensorInfo(  # type: ignore
                    label="", current=50, high=None, critical=None
                ),
            ],
            "coretemp": [
                pypsutil.TempSensorInfo(  # type: ignore
                    label="", current=60, high=100, critical=100
                ),
                pypsutil.TempSensorInfo(  # type: ignore
                    label="Chassis", current=90, high=None, critical=None
                ),
            ],
            "coretemp2": [
                pypsutil.TempSensorInfo(  # type: ignore
                    label="", current=60, high=100, critical=100
                ),
                pypsutil.TempSensorInfo(  # type: ignore
                    label="Chassis", current=90, high=None, critical=None
                ),
            ],
        }

    shutil.rmtree(tmp_path / "class")

    with replace_info_directories(sysfs=str(tmp_path)):
        assert pypsutil.sensors_temperatures() == {}  # type: ignore


@linux_only  # type: ignore
def test_temp_sensor_farenheit() -> None:
    sensor_a = pypsutil.TempSensorInfo(  # type: ignore
        label="sensor_a", current=0, high=100, critical=100
    )
    assert sensor_a.current_farenheit == 32
    assert sensor_a.high_farenheit == 212
    assert sensor_a.critical_farenheit == 212

    sensor_b = pypsutil.TempSensorInfo(  # type: ignore
        label="sensor_b", current=100, high=None, critical=None
    )
    assert sensor_b.current_farenheit == 212
    assert sensor_b.high_farenheit is None
    assert sensor_b.critical_farenheit is None
