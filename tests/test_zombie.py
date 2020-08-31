import sys

import pytest

import pypsutil

from .util import managed_zombie_process


def test_zombie_status() -> None:
    with managed_zombie_process() as proc:
        assert proc.status() == pypsutil.ProcessStatus.ZOMBIE


@pytest.mark.skipif(sys.platform != "linux", reason="Tests Linux-specific behavior")  # type: ignore
def test_cmdline_zombie() -> None:
    with managed_zombie_process() as proc:
        with pytest.raises(pypsutil.ZombieProcess):
            proc.cmdline()


@pytest.mark.skipif(sys.platform != "linux", reason="Tests Linux-specific behavior")  # type: ignore
def test_umask_zombie() -> None:
    with managed_zombie_process() as proc:
        with pytest.raises(pypsutil.ZombieProcess):
            proc.umask()
