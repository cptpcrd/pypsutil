import os
import pathlib
import time

import pytest

import pypsutil

from .util import linux_only, replace_info_directories


def test_boot_time() -> None:
    assert pypsutil.boot_time() <= time.time()


def test_time_since_boot() -> None:
    # Make sure they match up approximately
    assert time.time() == pytest.approx(pypsutil.boot_time() + pypsutil.time_since_boot(), abs=0.1)


if hasattr(pypsutil, "uptime"):

    def test_uptime() -> None:
        # time_since_boot() should always be greater than or equal to uptime()
        # Allow some minor flexibility, though
        assert pypsutil.time_since_boot() + 0.1 >= pypsutil.uptime()


def test_physical_cpu_count() -> None:
    logical_count = os.cpu_count()
    phys_count = pypsutil.physical_cpu_count()

    if logical_count is not None and phys_count is not None:
        assert phys_count <= logical_count


def test_percpu_info() -> None:
    ncpus = os.cpu_count()
    if not ncpus:
        pytest.skip("Unable to detect number of CPUs")

    if hasattr(pypsutil, "percpu_times"):
        assert len(pypsutil.percpu_times()) == ncpus

    if hasattr(pypsutil, "percpu_freq"):
        assert len(pypsutil.percpu_freq()) in (0, ncpus)


if hasattr(pypsutil, "cpu_freq"):

    def test_cpu_freq_range() -> None:
        freqs = pypsutil.cpu_freq()
        if freqs is None:
            pytest.skip("Unable to determine CPU frequencies")

        assert freqs.current > 0
        assert freqs.min == 0.0 or freqs.current >= freqs.min
        assert freqs.max == 0.0 or freqs.current <= freqs.max


if hasattr(pypsutil, "percpu_freq"):

    def test_percpu_freq_range() -> None:
        all_freqs = pypsutil.percpu_freq()
        if not all_freqs:
            pytest.skip("Unable to determine CPU frequencies")

        for freqs in all_freqs:
            assert freqs.current > 0
            assert freqs.min == 0.0 or freqs.current >= freqs.min
            assert freqs.max == 0.0 or freqs.current <= freqs.max


@linux_only
def test_cpu_info(tmp_path: pathlib.Path) -> None:
    with replace_info_directories(procfs=str(tmp_path)):
        # /proc/cpuinfo doesn't exist
        assert pypsutil.physical_cpu_count() is None

        # /proc/cpuinfo is an empty file
        with open(tmp_path / "cpuinfo", "w", encoding="utf8") as file:
            pass
        assert pypsutil.physical_cpu_count() is None

        # /proc/cpuinfo contains insufficient data
        with open(tmp_path / "cpuinfo", "w", encoding="utf8") as file:
            file.write("processor\t: 0\ncore id:\t0\n")
        assert pypsutil.physical_cpu_count() is None

        # Some entries in /proc/cpuinfo contain insufficient data
        with open(tmp_path / "cpuinfo", "w", encoding="utf8") as file:
            file.write(
                """
core id\t: 0
physical id\t: 0

core id\t: 1
""".lstrip()
            )
        assert pypsutil.physical_cpu_count() is None

        # Some entries in /proc/cpuinfo contain insufficient data
        with open(tmp_path / "cpuinfo", "w", encoding="utf8") as file:
            file.write(
                """
core id\t: 0
physical id\t: 0

core id\t: 0
physical id\t: 0


core id\t: 0
physical id\t: 1

core id\t: 1
physical id\t: 1
""".lstrip()
            )
        assert pypsutil.physical_cpu_count() == 3
