# pylint: disable=no-member
import os
import pathlib

import pytest

import pypsutil

from .util import linux_only, populate_directory, replace_info_directories

if hasattr(pypsutil.Process, "cpu_num"):

    def test_cpu_num_valid() -> None:
        ncpus = os.cpu_count()
        assert ncpus

        for proc in pypsutil.process_iter():
            try:
                cpu = proc.cpu_num()
            except pypsutil.NoSuchProcess:
                continue

            assert cpu == -1 or 0 <= cpu < ncpus


@linux_only
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


@linux_only
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


@linux_only
def test_cpu_freq_none(tmp_path: pathlib.Path) -> None:
    populate_directory(
        str(tmp_path),
        {"sysfs": {}, "procfs": {}},
    )

    with replace_info_directories(sysfs=str(tmp_path / "sysfs"), procfs=str(tmp_path / "procfs")):
        assert pypsutil.percpu_freq() == []  # type: ignore

        assert pypsutil.cpu_freq() is None  # type: ignore


@linux_only
def test_cpu_stats(tmp_path: pathlib.Path) -> None:
    with open(tmp_path / "stat", "w", encoding="utf8") as file:
        file.write(
            """cpu 0 0 0 0 0 0 0 0 0 0
cpu0 0 0 0 0 0 0 0 0 0 0
page 0 0
swap 0 0
intr 1234 10 24 425
ctxt 455
btime 0
processes 100
procs_running 1
procs_blocked 0
softirq 900 0 500 400
"""
        )

    with replace_info_directories(procfs=str(tmp_path)):
        assert pypsutil.cpu_stats() == pypsutil.CPUStats(  # type: ignore
            ctx_switches=455,
            interrupts=1234,
            soft_interrupts=900,
            syscalls=0,
        )


CLK_TCK = os.sysconf(os.sysconf_names["SC_CLK_TCK"])


@linux_only
def test_cpu_times(tmp_path: pathlib.Path) -> None:
    with open(tmp_path / "stat", "w", encoding="utf8") as file:
        file.write(
            """cpu {}
cpu0 0 0 0 0 0 0 0 0 0 0
page 0 0
swap 0 0
""".format(
                # This has an extra field to test how pypsutil handles that
                " ".join(str(val * CLK_TCK) for val in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
            )
        )

    with replace_info_directories(procfs=str(tmp_path)):
        assert pypsutil.cpu_times() == pypsutil.CPUTimes(  # type: ignore
            user=1,
            nice=2,
            system=3,
            idle=4,
            iowait=5,
            irq=6,
            softirq=7,
            steal=8,
            guest=9,
            guest_nice=10,
        )


@linux_only
def test_cpu_times_empty(tmp_path: pathlib.Path) -> None:
    # No "cpu" or "cpuN" entries
    with open(tmp_path / "stat", "w", encoding="utf8") as file:
        file.write("page 0 0\nswap 0 0\n")

    with replace_info_directories(procfs=str(tmp_path)):
        with pytest.raises(RuntimeError):
            pypsutil.cpu_times()  # type: ignore

        assert pypsutil.percpu_times() == []  # type: ignore


@linux_only
def test_percpu_times(tmp_path: pathlib.Path) -> None:
    with open(tmp_path / "stat", "w", encoding="utf8") as file:
        file.write(
            """cpu 0 0 0 0 0 0 0 0 0 0
cpu0 {}
cpu1 {}
page 0 0
swap 0 0
""".format(
                " ".join(str(val * CLK_TCK) for val in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]),
                # This has an extra field to test how pypsutil handles that
                " ".join(str(val * CLK_TCK) for val in [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]),
            )
        )

    with replace_info_directories(procfs=str(tmp_path)):
        assert pypsutil.percpu_times() == [  # type: ignore
            pypsutil.CPUTimes(  # type: ignore
                user=1,
                nice=2,
                system=3,
                idle=4,
                iowait=5,
                irq=6,
                softirq=7,
                steal=8,
                guest=9,
                guest_nice=10,
            ),
            pypsutil.CPUTimes(  # type: ignore
                user=2,
                nice=3,
                system=4,
                idle=5,
                iowait=6,
                irq=7,
                softirq=8,
                steal=9,
                guest=10,
                guest_nice=11,
            ),
        ]
