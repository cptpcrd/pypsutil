import sys

import pytest

import pypsutil

from .util import get_dead_process, managed_child_process

if hasattr(pypsutil.Process, "num_fds"):

    def test_num_fds() -> None:
        with managed_child_process(
            [sys.executable, "-c", "import time; time.sleep(10)"], close_fds=True
        ) as proc:
            assert proc.num_fds() == 3

    def test_num_fds_no_proc() -> None:
        proc = get_dead_process()

        with pytest.raises(pypsutil.NoSuchProcess):
            proc.num_fds()
