# pylint: disable=no-member
import pathlib

import pypsutil

from .util import linux_only, populate_directory, replace_info_directories


@linux_only  # type: ignore
def test_cpu_freq_sysfs(tmp_path: pathlib.Path) -> None:
    populate_directory(
        str(tmp_path),
        {
            "devices": {
                "system": {
                    "cpu": {
                        "cpu0": {
                            "cpufreq": {
                                "scaling_min_freq": "1000000",
                                "scaling_cur_freq": "2000000",
                                "scaling_max_freq": "3000000",
                            },
                        },
                        "cpu1": {
                            "cpufreq": {
                                "scaling_min_freq": "1500000",
                                "scaling_cur_freq": "2500000",
                                "scaling_max_freq": "3500000",
                            },
                        },
                        "online": "0-4",
                    }
                }
            }
        },
    )

    with replace_info_directories(sysfs=str(tmp_path)):
        assert pypsutil.percpu_freq() == [  # type: ignore
            pypsutil.CPUFrequencies(current=2000, min=1000, max=3000),
            pypsutil.CPUFrequencies(current=2500, min=1500, max=3500),
        ]

        assert pypsutil.cpu_freq() == (  # type: ignore
            pypsutil.CPUFrequencies(current=2250, min=1250, max=3250)
        )


@linux_only  # type: ignore
def test_cpu_freq_procfs(tmp_path: pathlib.Path) -> None:
    populate_directory(
        str(tmp_path),
        {
            "sysfs": {"devices": {"system": {"cpu": {}}}},
            "procfs": {
                "cpuinfo": """
core id: 0
physical id: 0
cpu MHz: 2000

core id: 1
physical id: 0
cpu MHz: 2500
"""
            },
        },
    )

    with replace_info_directories(sysfs=str(tmp_path / "sysfs"), procfs=str(tmp_path / "procfs")):
        assert pypsutil.percpu_freq() == [  # type: ignore
            pypsutil.CPUFrequencies(current=2000, min=0, max=0),
            pypsutil.CPUFrequencies(current=2500, min=0, max=0),
        ]

        assert pypsutil.cpu_freq() == (  # type: ignore
            pypsutil.CPUFrequencies(current=2250, min=0, max=0)
        )


@linux_only  # type: ignore
def test_cpu_freq_none(tmp_path: pathlib.Path) -> None:
    populate_directory(
        str(tmp_path),
        {"sysfs": {}, "procfs": {}},
    )

    with replace_info_directories(sysfs=str(tmp_path / "sysfs"), procfs=str(tmp_path / "procfs")):
        assert pypsutil.percpu_freq() == []  # type: ignore

        assert pypsutil.cpu_freq() is None  # type: ignore
