import time

import pypsutil


def test_boot_time() -> None:
    assert pypsutil.boot_time() <= time.time()
