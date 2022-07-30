import os

import pytest

import pypsutil

from .util import get_dead_process


@pytest.mark.skipif(
    not hasattr(pypsutil.Process, "cpu_getaffinity"), reason="Tests getting CPU affinity"
)
def test_getaffinity() -> None:
    ncpus = os.cpu_count()
    assert ncpus

    cpus = pypsutil.Process().cpu_getaffinity()
    assert cpus

    assert min(cpus) >= 0
    assert max(cpus) < ncpus


@pytest.mark.skipif(
    not hasattr(pypsutil.Process, "cpu_getaffinity"), reason="Tests errors getting CPU affinity"
)
def test_getaffinity_no_proc() -> None:
    proc = get_dead_process()

    with pytest.raises(pypsutil.NoSuchProcess):
        proc.cpu_getaffinity()


@pytest.mark.skipif(
    not hasattr(pypsutil.Process, "cpu_getaffinity")
    or not hasattr(pypsutil.Process, "cpu_setaffinity"),
    reason="Tests getting/setting CPU affinity",
)
def test_getsetaffinity() -> None:
    orig_cpus = pypsutil.Process().cpu_getaffinity()

    cpu = next(iter(orig_cpus))
    pypsutil.Process().cpu_setaffinity([cpu])
    assert pypsutil.Process().cpu_getaffinity() == {cpu}

    pypsutil.Process().cpu_setaffinity([])
    cpus = pypsutil.Process().cpu_getaffinity()
    assert cpus >= orig_cpus
    assert len(cpus) <= (os.cpu_count() or 1)

    pypsutil.Process().cpu_setaffinity(orig_cpus)
    assert pypsutil.Process().cpu_getaffinity() == orig_cpus


@pytest.mark.skipif(
    not hasattr(pypsutil.Process, "cpu_setaffinity"), reason="Tests errors setting CPU affinity"
)
def test_setaffinity_errors() -> None:
    with pytest.raises(ValueError):
        pypsutil.Process().cpu_setaffinity([-1])

    with pytest.raises((ValueError, OverflowError)):
        pypsutil.Process().cpu_setaffinity([2**32])


@pytest.mark.skipif(
    not hasattr(pypsutil.Process, "cpu_setaffinity"), reason="Tests errors setting CPU affinity"
)
def test_setaffinity_no_proc() -> None:
    proc = get_dead_process()

    with pytest.raises(pypsutil.NoSuchProcess):
        proc.cpu_setaffinity([])

    with pytest.raises(pypsutil.NoSuchProcess):
        proc.cpu_setaffinity([0])
