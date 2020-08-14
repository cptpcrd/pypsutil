import fcntl
import os
import pty
import sys
import termios

import pytest

import pypsutil

from .util import fork_proc


def test_terminal() -> None:
    # Open a PTY
    master_fd, slave_fd = pty.openpty()

    # Spawn a child. Have it:
    # 1. Set the PTY we just opened as its controlling terminal
    # 2. Close both master_fd and slave_fd
    # 3. write() some data to the PTY so the parent can see if it's gotten that far
    # 4. Try to read() some data from the PTY (this will hang, and when the parent
    #    closes the PTY it will raise an exception)
    proc = fork_proc(
        lambda: [  # type: ignore
            os.setsid(),  # type: ignore
            fcntl.ioctl(slave_fd, termios.TIOCSCTTY, 0),
            os.close(master_fd),  # type: ignore
            os.dup2(slave_fd, 0),
            os.dup2(slave_fd, 1),
            os.dup2(slave_fd, 2),
            os.close(slave_fd),  # type: ignore
            os.write(1, b"\n"),
            os.read(0, 1),
        ]
    )

    # Get the name of the slave end, then close it
    slave_name = os.ttyname(slave_fd)
    os.close(slave_fd)

    try:
        # Wait for the slave to signal that it's ready
        assert os.read(master_fd, 2) == b"\r\n"

        # Check that the name matches
        assert proc.terminal() == slave_name
    finally:
        # Close the master end and wait for the child to exit
        os.close(master_fd)
        os.waitpid(proc.pid, 0)


def test_no_terminal() -> None:
    parent_r, child_w = os.pipe()
    parent_w, child_r = os.pipe()

    proc = fork_proc(
        lambda: [  # type: ignore
            # Close the parent ends of the pipes
            os.close(parent_r),  # type: ignore
            os.close(parent_w),  # type: ignore
            # New session
            os.setsid(),  # type: ignore
            # Tell the parent we're ready, and wait for it to close the pipes
            os.write(child_w, b"\n"),
            os.read(child_r, 1),
        ]
    )

    os.close(child_r)
    os.close(child_w)

    assert os.read(parent_r, 1) == b"\n"

    try:
        assert proc.terminal() is None
    finally:
        # Close the pipes and wait for the child to exit
        os.close(parent_r)
        os.close(parent_w)
        os.waitpid(proc.pid, 0)


def test_terminal_no_proc() -> None:
    proc = fork_proc(lambda: sys.exit(0))
    os.waitpid(proc.pid, 0)

    with pytest.raises(pypsutil.NoSuchProcess):
        proc.terminal()

    with proc.oneshot():
        with pytest.raises(pypsutil.NoSuchProcess):
            proc.terminal()
