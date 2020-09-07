import os
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


if hasattr(pypsutil.Process, "open_files"):

    def test_open_files_empty() -> None:
        with managed_child_process2(
            [sys.executable, "-c", "import time; print('a', flush=True); time.sleep(10)"],
            close_fds=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=0,
        ) as proc:
            assert proc.stdout is not None
            assert proc.stdout.read(1) == b"a"

            assert proc.open_files() == []

    def test_open_files_2() -> None:
        with managed_child_process2(
            [
                sys.executable,
                "-c",
                """
import os, sys, time
os.open("/", os.O_RDONLY)
os.open(sys.executable, os.O_RDONLY)
print('a', flush=True)
time.sleep(10)
""",
            ],
            close_fds=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=0,
        ) as proc:
            assert proc.stdout is not None
            assert proc.stdout.read(1) == b"a"

            open_files = proc.open_files()

            assert len(open_files) == 1
            assert open_files[0].fd == 4
            if open_files[0].path:
                assert os.path.samefile(open_files[0].path, sys.executable)

    def test_open_files_no_proc() -> None:
        proc = get_dead_process()

        with pytest.raises(pypsutil.NoSuchProcess):
            proc.open_files()
