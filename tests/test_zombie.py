import pytest

import pypsutil

from .util import linux_only, managed_zombie_process


def test_zombie_status() -> None:
    with managed_zombie_process() as proc:
        assert proc.status() == pypsutil.ProcessStatus.ZOMBIE


@linux_only  # type: ignore
def test_cmdline_zombie() -> None:
    with managed_zombie_process() as proc:
        with pytest.raises(pypsutil.ZombieProcess):
            proc.cmdline()


@linux_only  # type: ignore
def test_umask_zombie() -> None:
    with managed_zombie_process() as proc:
        with pytest.raises(pypsutil.ZombieProcess):
            proc.umask()
