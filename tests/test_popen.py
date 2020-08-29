import subprocess
import sys

import pytest

import pypsutil


def test_popen_launch_error() -> None:
    with pytest.raises(OSError, match="No such file or directory"):
        pypsutil.Popen(["./NOEXIST"])

    with pytest.raises(OSError, match="No such file or directory"):
        pypsutil.Popen(["NOEXIST"])


def test_popen_success() -> None:
    proc = pypsutil.Popen([sys.executable, "-c", ""])

    retval = proc.wait()
    assert retval is not None

    assert proc.poll() == retval
    assert proc.wait() == retval
    assert proc.wait(0.0) == retval
    assert proc.returncode == retval


def test_popen_wait() -> None:
    proc = pypsutil.Popen([sys.executable, "-c", "import time; time.sleep(10)"])

    assert proc.poll() is None

    with pytest.raises(pypsutil.TimeoutExpired):
        proc.wait(0)

    proc.terminate()

    retval = proc.wait()
    assert retval is not None

    assert proc.poll() == retval
    assert proc.wait() == retval
    assert proc.wait(0.0) == retval
    assert proc.returncode == retval


def test_popen_communicate() -> None:
    proc = pypsutil.Popen(
        [sys.executable, "-c", "import sys; print(1); print(2, file=sys.stderr)"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert proc.communicate() == (b"1\n", b"2\n")

    proc = pypsutil.Popen(
        [sys.executable, "-c", "print(input())"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert proc.communicate(b"1\n") == (b"1\n", b"")

    proc = pypsutil.Popen([sys.executable, "-c", "import time; time.sleep(10)"])
    with pytest.raises(pypsutil.TimeoutExpired):
        proc.communicate(timeout=0)

    proc.terminate()
    proc.wait()


def test_popen_context() -> None:
    with pypsutil.Popen([sys.executable, "-c", "import time; time.sleep(10)"]) as proc:
        proc.terminate()

        # proc.returncode should NOT be set yet
        assert proc.returncode is None

    # Popen.__exit__() will wait for the process, so proc.returncode should be set now
    assert proc.returncode is not None

    with pypsutil.Popen(
        [sys.executable, "-c", "import time; time.sleep(10)"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as proc:
        proc.terminate()

        assert proc.returncode is None
        assert not proc.stdin.closed
        assert not proc.stdout.closed
        assert not proc.stderr.closed

    assert proc.returncode is not None
    assert proc.stdin.closed
    assert proc.stdout.closed
    assert proc.stderr.closed
