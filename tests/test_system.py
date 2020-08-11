import time

import pypsutil


def test_boot_time() -> None:
    assert pypsutil.boot_time() <= time.time()


def test_time_since_boot() -> None:
    # Make sure they match up approximately
    assert round(time.time() - (pypsutil.boot_time() + pypsutil.time_since_boot()), 1) == 0


if hasattr(pypsutil, "uptime"):

    def test_uptime() -> None:
        # time_since_boot() should always be greater than or equal to uptime()
        # Allow some minor flexibility, though
        assert pypsutil.time_since_boot() - pypsutil.uptime() >= -1
