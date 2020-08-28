import os
import time

import pypsutil


def test_boot_time() -> None:
    assert pypsutil.boot_time() <= time.time()


def test_time_since_boot() -> None:
    # Make sure they match up approximately
    assert round(time.time() - (pypsutil.boot_time() + pypsutil.time_since_boot()), 1) == 0


def test_physical_cpu_count() -> None:
    logical_count = os.cpu_count()
    phys_count = pypsutil.physical_cpu_count()

    if logical_count is not None and phys_count is not None:
        assert phys_count <= logical_count
