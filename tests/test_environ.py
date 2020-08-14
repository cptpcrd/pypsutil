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

        proc_env = proc.environ()
    finally:
        subproc.terminate()
        subproc.wait()

    # Check that env is a subset of proc.environ()
    # On macOS, proc.environ() includes some extra ifnormation
    for name in env:
        assert env[name] == proc_env[name]


def test_environ_no_proc() -> None:
    subproc = subprocess.Popen([sys.executable, "-c", "exit()"])

    try:
        proc = pypsutil.Process(subproc.pid)
    finally:
        subproc.wait()

    with pytest.raises(pypsutil.NoSuchProcess):
        proc.environ()
