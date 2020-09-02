import subprocess
import sys

import pytest

import pypsutil

from .util import get_dead_process, managed_child_process2

if hasattr(pypsutil.Process, "num_fds"):

    def test_num_fds() -> None:
        with managed_child_process2(
            [sys.executable, "-c", "import time; print('a', flush=True); time.sleep(10)"],
            close_fds=True,
            stdout=subprocess.PIPE,
            bufsize=0,
        ) as proc:
            assert proc.stdout is not None
            assert proc.stdout.read(1) == b"a"

            assert proc.num_fds() == 3

    def test_num_fds_no_proc() -> None:
        proc = get_dead_process()

        with pytest.raises(pypsutil.NoSuchProcess):
            proc.num_fds()
