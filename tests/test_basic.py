import os
import sys
import time

import pytest

import pypsutil

from .util import get_dead_process, managed_child_process


def test_basic_info() -> None:
    proc = pypsutil.Process()

    assert proc.pid == os.getpid()
    assert proc.ppid() == os.getppid()
    assert proc.pgid() == os.getpgrp()
    assert proc.sid() == os.getsid(0)

    assert proc.status() == pypsutil.ProcessStatus.RUNNING

    assert proc.parent().pid == os.getppid()  # type: ignore

    assert proc.create_time() <= time.time()
    assert proc.create_time() >= pypsutil.boot_time()

    assert os.path.samefile(proc.cwd(), os.getcwd())


def test_basic_info_oneshot() -> None:
    proc = pypsutil.Process()

    with proc.oneshot():
        assert proc.pid == os.getpid()
        assert proc.ppid() == os.getppid()
        assert proc.pgid() == os.getpgrp()
        assert proc.sid() == os.getsid(0)

        assert proc.status() == pypsutil.ProcessStatus.RUNNING

        assert proc.parent().pid == os.getppid()  # type: ignore

        assert proc.create_time() <= time.time()
        assert proc.create_time() >= pypsutil.boot_time()

        assert os.path.samefile(proc.cwd(), os.getcwd())


def test_oneshot_nested() -> None:
    proc = pypsutil.Process()

    with proc.oneshot():
        with proc.oneshot():
            assert proc.pid == os.getpid()


def test_basic_info_pid_0() -> None:
    try:
        proc = pypsutil.Process(0)
    except pypsutil.NoSuchProcess:
        pytest.skip("PID 0 does not appear")

    assert proc.pgid() == 0
    assert proc.sid() == 0


def test_basic_info_no_proc() -> None:
    proc = get_dead_process()

    with pytest.raises(pypsutil.NoSuchProcess):
        proc.ppid()

    with pytest.raises(pypsutil.NoSuchProcess):
        proc.pgid()

    with pytest.raises(pypsutil.NoSuchProcess):
        proc.sid()

    with pytest.raises(pypsutil.NoSuchProcess):
        proc.cwd()


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

    with managed_child_process([sys.executable, "-c", "exit()"]) as child_proc:
        assert child_proc.ppid() == cur_proc.pid
        assert child_proc.parent() == cur_proc


if hasattr(pypsutil.Process, "umask"):

    def test_umask() -> None:
        proc = pypsutil.Process()

        mask = proc.umask()
        if mask is not None:
            assert os.umask(mask) == mask

    def test_umask_no_proc() -> None:
        proc = get_dead_process()

        with pytest.raises(pypsutil.NoSuchProcess):
            proc.umask()


if hasattr(pypsutil.Process, "root"):

    def test_root() -> None:
        proc = pypsutil.Process()

        assert proc.root() == "/"

    def test_root_no_proc() -> None:
        proc = get_dead_process()

        with pytest.raises(pypsutil.NoSuchProcess):
            proc.root()
