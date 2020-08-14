import resource

import pytest

import pypsutil
from pypsutil._util import RESOURCE_NUMS

from .util import get_dead_process

if hasattr(pypsutil.Process, "rlimit"):

    def test_proc_rlimit() -> None:
        limits = resource.getrlimit(resource.RLIMIT_NOFILE)

        proc = pypsutil.Process()

        assert proc.rlimit(resource.RLIMIT_NOFILE) == limits
        assert proc.rlimit(resource.RLIMIT_NOFILE, limits) == limits

        with proc.oneshot():
            assert proc.rlimit(resource.RLIMIT_NOFILE) == limits
            assert proc.rlimit(resource.RLIMIT_NOFILE, limits) == limits

    def test_proc_rlimit_no_proc() -> None:
        proc = get_dead_process()

        with pytest.raises(pypsutil.NoSuchProcess):
            proc.rlimit(resource.RLIMIT_NOFILE)

        with pytest.raises(pypsutil.NoSuchProcess):
            proc.rlimit(resource.RLIMIT_NOFILE, resource.getrlimit(resource.RLIMIT_NOFILE))

        with proc.oneshot():
            with pytest.raises(pypsutil.NoSuchProcess):
                proc.rlimit(resource.RLIMIT_NOFILE)

            with pytest.raises(pypsutil.NoSuchProcess):
                proc.rlimit(resource.RLIMIT_NOFILE, resource.getrlimit(resource.RLIMIT_NOFILE))

    def test_proc_rlimit_error() -> None:
        proc = pypsutil.Process()

        with pytest.raises(ValueError, match=r"^current limit exceeds maximum limit$"):
            proc.rlimit(resource.RLIMIT_NOFILE, (1, 0))

        with pytest.raises(ValueError, match=r"^current limit exceeds maximum limit$"):
            proc.rlimit(resource.RLIMIT_NOFILE, (resource.RLIM_INFINITY, 0))

        with pytest.raises(ValueError, match=r"^current limit exceeds maximum limit$"):
            proc.rlimit(resource.RLIMIT_NOFILE, (-2, 0))

        with pytest.raises(ValueError, match=r"^invalid resource specified$"):
            proc.rlimit(max(RESOURCE_NUMS) + 1)

        with pytest.raises(OverflowError):
            proc.rlimit(resource.RLIMIT_NOFILE, (2 ** 64, -1))

        with pytest.raises(OverflowError):
            proc.rlimit(resource.RLIMIT_NOFILE, (2 ** 31 - 1, 2 ** 64))


if hasattr(pypsutil.Process, "getrlimit"):

    def test_proc_getrlimit() -> None:
        proc = pypsutil.Process()

        assert proc.getrlimit(resource.RLIMIT_NOFILE) == resource.getrlimit(resource.RLIMIT_NOFILE)

        with proc.oneshot():
            assert proc.getrlimit(resource.RLIMIT_NOFILE) == resource.getrlimit(
                resource.RLIMIT_NOFILE
            )

    def test_proc_getrlimit_no_proc() -> None:
        proc = get_dead_process()

        with pytest.raises(pypsutil.NoSuchProcess):
            proc.getrlimit(resource.RLIMIT_NOFILE)

        with proc.oneshot():
            with pytest.raises(pypsutil.NoSuchProcess):
                proc.getrlimit(resource.RLIMIT_NOFILE)

    def test_proc_getrlimit_error() -> None:
        proc = pypsutil.Process()

        with pytest.raises(ValueError, match=r"^invalid resource specified$"):
            proc.getrlimit(max(RESOURCE_NUMS) + 1)
