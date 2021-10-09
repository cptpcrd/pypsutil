import os

import pytest

import pypsutil


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
    not hasattr(pypsutil.Process, "cpu_getaffinity")
    or not hasattr(pypsutil.Process, "cpu_setaffinity"),
    reason="Tests getting/setting CPU affinity",
)
def test_getsetaffinity() -> None:
    orig_cpus = pypsutil.Process().cpu_getaffinity()

    cpu = next(iter(orig_cpus))
    pypsutil.Process().cpu_setaffinity([cpu])
    assert pypsutil.Process().cpu_getaffinity() == {cpu}

    pypsutil.Process().cpu_setaffinity(orig_cpus)
    assert pypsutil.Process().cpu_getaffinity() == orig_cpus

    with pytest.raises(OSError):
        pypsutil.Process().cpu_setaffinity([])
