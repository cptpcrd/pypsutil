import os
import sys
import time

import pytest

import pypsutil

from .util import fork_proc


def test_basic_info() -> None:
    proc = pypsutil.Process()

    assert proc.pid == os.getpid()
    assert proc.ppid() == os.getppid()
    assert proc.pgid() == os.getpgrp()
    assert proc.sid() == os.getsid(0)

    assert proc.parent().pid == os.getppid()  # type: ignore

    assert proc.create_time() <= time.time()
    assert proc.create_time() >= pypsutil.boot_time()

    assert os.path.samefile(proc.cwd(), os.getcwd())
    assert os.path.samefile(proc.exe(), sys.executable)

    # environ() may not reflect changes since startup,
    # so we can't do a simple comparison.
    proc_environ = proc.environ()
    assert proc_environ
    assert os.environ.get("PATH") == proc_environ.get("PATH")
    assert os.environ.get("USER") == proc_environ.get("USER")
    assert os.environ.get("LANG") == proc_environ.get("LANG")


def test_basic_info_no_proc() -> None:
    proc = fork_proc(lambda: sys.exit(0))
    os.waitpid(proc.pid, 0)

    with pytest.raises(pypsutil.NoSuchProcess):
        proc.ppid()

    with pytest.raises(pypsutil.NoSuchProcess):
        proc.pgid()

    with pytest.raises(pypsutil.NoSuchProcess):
        proc.sid()

    with pytest.raises(pypsutil.NoSuchProcess):
        proc.cwd()

    with pytest.raises(pypsutil.NoSuchProcess):
        proc.exe()

    with pytest.raises(pypsutil.NoSuchProcess):
        proc.environ()


def test_negative_pid() -> None:
    with pytest.raises(pypsutil.NoSuchProcess):
        pypsutil.Process(-1)


def test_parents() -> None:
    proc = pypsutil.Process()

    for parent in proc.parents():
        proc = proc.parent()  # type: ignore
        assert proc == parent

    assert proc.parent() is None


def test_parent() -> None:
    cur_proc = pypsutil.Process()
    child_proc = fork_proc(lambda: sys.exit(0))

    assert child_proc.ppid() == cur_proc.pid
    assert child_proc.parent() == cur_proc

    os.waitpid(child_proc.pid, 0)


if hasattr(pypsutil.Process, "umask"):

    def test_umask() -> None:
        proc = pypsutil.Process()

        mask = proc.umask()
        if mask is not None:
            assert os.umask(mask) == mask

    def test_umask_no_proc() -> None:
        proc = fork_proc(lambda: sys.exit(0))
        os.waitpid(proc.pid, 0)

        with pytest.raises(pypsutil.NoSuchProcess):
            proc.umask()


if hasattr(pypsutil.Process, "root"):

    def test_root() -> None:
        proc = pypsutil.Process()

        assert proc.root() == "/"

    def test_root_no_proc() -> None:
        proc = fork_proc(lambda: sys.exit(0))
        os.waitpid(proc.pid, 0)

        with pytest.raises(pypsutil.NoSuchProcess):
            proc.root()
