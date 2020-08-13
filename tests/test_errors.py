import pypsutil


def test_nosuchprocess() -> None:
    ex = pypsutil.NoSuchProcess(12)

    assert ex.pid == 12
    assert str(ex) == "pypsutil.NoSuchProcess: process does not exist (pid=12)"
    assert repr(ex) == "pypsutil.NoSuchProcess(pid=12)"


def test_zombieprocess() -> None:
    ex = pypsutil.ZombieProcess(12)

    assert ex.pid == 12
    assert str(ex) == "pypsutil.ZombieProcess: process exists but is a zombie (pid=12)"
    assert repr(ex) == "pypsutil.ZombieProcess(pid=12)"


def test_accessdenied() -> None:
    ex = pypsutil.AccessDenied(12)

    assert ex.pid == 12
    assert str(ex) == "pypsutil.AccessDenied (pid=12)"
    assert repr(ex) == "pypsutil.AccessDenied(pid=12)"
