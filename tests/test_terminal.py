import os
import pty
import sys

import pytest

import pypsutil

from .util import get_dead_process, managed_child_process


def test_terminal() -> None:
    # Open a PTY
    master_fd, slave_fd = pty.openpty()

    # Spawn a child. Have it:
    # 1. Set the PTY we just opened as its controlling terminal
    # 2. Close slave_fd
    # 3. write() some data to the PTY so the parent can see if it's gotten that far
    # 4. Try to read() some data from the PTY (this will hang, and when the parent
    #    closes the PTY it will raise an exception)

    with managed_child_process(
        [
            sys.executable,
            "-c",
            r"""
import fcntl
import os
import sys
import termios

slave_fd = int(sys.argv[1])

fcntl.ioctl(slave_fd, termios.TIOCSCTTY, 0)
os.dup2(slave_fd, 0)
os.dup2(slave_fd, 1)
os.dup2(slave_fd, 2)
os.close(slave_fd)
os.write(1, b"\n")
os.read(0, 1)

""",
            str(slave_fd),
        ],
        pass_fds=[slave_fd],
        start_new_session=True,
    ) as proc:
        # Get the name of the slave end, then close it
        slave_name = os.ttyname(slave_fd)
        os.close(slave_fd)

        try:
            # Wait for the slave to signal that it's ready
            assert os.read(master_fd, 2) == b"\r\n"

            # Check that the name matches
            assert proc.terminal() == slave_name
        finally:
            # Close the master end
            os.close(master_fd)


def test_no_terminal() -> None:
    parent_r, child_w = os.pipe()
    parent_w, child_r = os.pipe()

    with managed_child_process(
        [
            sys.executable,
            "-c",
            r"""
import os
import sys

child_w = int(sys.argv[1])
child_r = int(sys.argv[2])

# Tell the parent we're ready, and wait for it to close the pipes
os.write(child_w, b"\n")
os.read(child_r, 1)

""",
            str(child_w),
            str(child_r),
        ],
        pass_fds=[child_w, child_r],
        start_new_session=True,
    ) as proc:
        os.close(child_r)
        os.close(child_w)

        assert os.read(parent_r, 1) == b"\n"

        try:
            assert proc.terminal() is None
        finally:
            # Close the pipes
            os.close(parent_r)
            os.close(parent_w)


def test_terminal_no_proc() -> None:
    proc = get_dead_process()

    with pytest.raises(pypsutil.NoSuchProcess):
        proc.terminal()

    with proc.oneshot():
        with pytest.raises(pypsutil.NoSuchProcess):
            proc.terminal()
