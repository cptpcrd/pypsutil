import os
import subprocess
import sys

import pytest

import pypsutil


def test_environ() -> None:
    env = dict(os.environ)

    subproc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(10)"], env=env)

    try:
        proc = pypsutil.Process(subproc.pid)

        assert proc.environ() == env
    finally:
        subproc.terminate()
        subproc.wait()


def test_environ_no_proc() -> None:
    subproc = subprocess.Popen([sys.executable, "-c", "exit()"])

    try:
        proc = pypsutil.Process(subproc.pid)
    finally:
        subproc.wait()

    with pytest.raises(pypsutil.NoSuchProcess):
        proc.environ()
