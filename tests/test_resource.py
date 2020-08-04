import os
import resource
import sys

import pytest

import pypsutil
from pypsutil._util import RESOURCE_NUMS

from .util import fork_proc

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
        proc = fork_proc(lambda: sys.exit(0))
        os.waitpid(proc.pid, 0)

        with pytest.raises(ProcessLookupError):
            proc.rlimit(resource.RLIMIT_NOFILE)

        with pytest.raises(ProcessLookupError):
            proc.rlimit(resource.RLIMIT_NOFILE, resource.getrlimit(resource.RLIMIT_NOFILE))

        with proc.oneshot():
            with pytest.raises(ProcessLookupError):
                proc.rlimit(resource.RLIMIT_NOFILE)

            with pytest.raises(ProcessLookupError):
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


if hasattr(pypsutil.Process, "getrlimit"):

    def test_proc_getrlimit() -> None:
        proc = pypsutil.Process()

        assert proc.getrlimit(resource.RLIMIT_NOFILE) == resource.getrlimit(resource.RLIMIT_NOFILE)

        with proc.oneshot():
            assert proc.getrlimit(resource.RLIMIT_NOFILE) == resource.getrlimit(
                resource.RLIMIT_NOFILE
            )

    def test_proc_getrlimit_no_proc() -> None:
        proc = fork_proc(lambda: sys.exit(0))
        os.waitpid(proc.pid, 0)

        with pytest.raises(ProcessLookupError):
            proc.getrlimit(resource.RLIMIT_NOFILE)

        with proc.oneshot():
            with pytest.raises(ProcessLookupError):
                proc.getrlimit(resource.RLIMIT_NOFILE)

    def test_proc_getrlimit_error() -> None:
        proc = pypsutil.Process()

        with pytest.raises(ValueError, match=r"^invalid resource specified$"):
            proc.getrlimit(max(RESOURCE_NUMS) + 1)
