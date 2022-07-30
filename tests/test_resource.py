import math
import os
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
            proc.rlimit(resource.RLIMIT_NOFILE, (2**64, -1))

        with pytest.raises(OverflowError):
            proc.rlimit(resource.RLIMIT_NOFILE, (2**31 - 1, 2**64))


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


def test_proc_cpu_times_self() -> None:
    proc = pypsutil.Process()

    cpu_times: pypsutil.ProcessCPUTimes = proc.cpu_times()
    os_times = os.times()

    assert math.isclose(cpu_times.user, os_times.user, abs_tol=0.05)
    assert math.isclose(cpu_times.system, os_times.system, abs_tol=0.05)


def test_proc_cpu_times_children() -> None:
    proc = pypsutil.Process()

    cpu_times: pypsutil.ProcessCPUTimes = proc.cpu_times()
    os_times = os.times()

    if pypsutil.OPENBSD or pypsutil.NETBSD:
        # Combined user + system
        assert cpu_times.children_user == cpu_times.children_system
        assert math.isclose(
            cpu_times.children_user, os_times.children_user + os_times.children_system, abs_tol=0.05
        )
    elif pypsutil.MACOS:
        assert cpu_times.children_user == 0
        assert cpu_times.children_system == 0
    else:
        assert math.isclose(cpu_times.children_user, os_times.children_user, abs_tol=0.05)
        assert math.isclose(cpu_times.children_system, os_times.children_system, abs_tol=0.05)


def test_proc_ctx_switches_self() -> None:
    pre_ru = resource.getrusage(resource.RUSAGE_SELF)
    ctx = pypsutil.Process().num_ctx_switches()
    post_ru = resource.getrusage(resource.RUSAGE_SELF)

    pre_rctx = pre_ru.ru_nvcsw + pre_ru.ru_nivcsw
    post_rctx = post_ru.ru_nvcsw + post_ru.ru_nivcsw

    assert pre_rctx <= ctx <= post_rctx
