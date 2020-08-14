import time

import pypsutil


def test_boot_time() -> None:
    assert pypsutil.boot_time() <= time.time()


def test_time_since_boot() -> None:
    # Make sure they match up approximately
    assert round(time.time() - (pypsutil.boot_time() + pypsutil.time_since_boot()), 1) == 0
