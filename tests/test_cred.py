# mypy: ignore-errors
import getpass
import os
import sys

import pytest

import pypsutil

from .util import get_dead_process


def test_uids() -> None:
    proc = pypsutil.Process()

    if hasattr(os, "getresuid"):
        assert proc.uids() == os.getresuid()  # pylint: disable=no-member
    else:
        ruid, euid, _ = proc.uids()
        assert ruid == os.getuid()
        assert euid == os.geteuid()


def test_gids() -> None:
    proc = pypsutil.Process()

    if hasattr(os, "getresgid"):
        assert proc.gids() == os.getresgid()  # pylint: disable=no-member
    else:
        rgid, egid, _ = proc.gids()
        assert rgid == os.getgid()
        assert egid == os.getegid()


def test_username() -> None:
    proc = pypsutil.Process()

    assert proc.username() == getpass.getuser()


def test_getgroups() -> None:
    proc = pypsutil.Process()

    groups = proc.getgroups()

    # Check for internal consistency when using oneshot()
    with proc.oneshot():
        assert set(groups) == set(proc.getgroups())

    cur_groups = os.getgroups()

    if sys.platform.startswith("darwin"):
        # getgroups() is not POSIX-compliant since macOS 10.5
        assert set(groups) <= set(cur_groups)
    else:
        # Check that the group list matches
        assert set(groups) == set(cur_groups)


def test_getgroups_no_proc() -> None:
    proc = get_dead_process()

    with pytest.raises(pypsutil.NoSuchProcess):
        proc.getgroups()

    with proc.oneshot():
        with pytest.raises(pypsutil.NoSuchProcess):
            proc.getgroups()
