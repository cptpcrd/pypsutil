import subprocess
import sys
import threading

import pytest

import pypsutil

from .util import get_dead_process

if hasattr(pypsutil.Process, "num_threads"):

    def test_num_threads_cur() -> None:
        proc = pypsutil.Process()

        assert proc.num_threads() == threading.active_count()

    def test_num_threads_subproc() -> None:
        with pypsutil.Popen(
            [
                sys.executable,
                "-c",
                "import time, threading; threading.Thread(target=time.sleep, args=(10,)).start(); "
                "print('a', flush=True); time.sleep(10)",
            ],
            stdout=subprocess.PIPE,
        ) as proc:
            try:
                assert proc.stdout is not None
                assert proc.stdout.read(1) == b"a"

                assert proc.num_threads() == 2
            finally:
                proc.terminate()

    def test_num_threads_no_proc() -> None:
        proc = get_dead_process()

        with pytest.raises(pypsutil.NoSuchProcess):
            proc.num_threads()
