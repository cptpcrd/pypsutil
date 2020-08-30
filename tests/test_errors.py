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


def test_timeoutexpired() -> None:
    ex1 = pypsutil.TimeoutExpired(1.2)

    assert ex1.seconds == 1.2
    assert ex1.pid is None
    assert str(ex1) == "pypsutil.TimeoutExpired: timeout after 1.2 seconds"
    assert repr(ex1) == "pypsutil.TimeoutExpired(1.2, pid=None)"

    ex2 = pypsutil.TimeoutExpired(3, 10)

    assert ex2.seconds == 3
    assert ex2.pid == 10
    assert str(ex2) == "pypsutil.TimeoutExpired: timeout after 3 seconds (pid=10)"
    assert repr(ex2) == "pypsutil.TimeoutExpired(3, pid=10)"
