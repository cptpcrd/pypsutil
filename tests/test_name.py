import os
import subprocess
import sys

import pytest

import pypsutil


def test_cmdline() -> None:
    args = [sys.executable, "-c", "import time; time.sleep(10)"]

    subproc = subprocess.Popen(args)

    try:
        proc = pypsutil.Process(subproc.pid)

        assert proc.name() == os.path.basename(sys.executable)
    finally:
        subproc.terminate()
        subproc.wait()


def test_name_no_proc() -> None:
    subproc = subprocess.Popen([sys.executable, "-c", "exit()"])

    try:
        proc = pypsutil.Process(subproc.pid)
    finally:
        subproc.wait()

    with pytest.raises(pypsutil.NoSuchProcess):
        proc.name()
