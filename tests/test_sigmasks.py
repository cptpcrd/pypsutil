# mypy: ignore-errors
import os
import signal
import sys
import threading
from typing import Any

import pytest

import pypsutil

from .util import get_dead_process

if sys.platform.startswith(("linux", "darwin", "freebsd", "openbsd", "netbsd")):

    def test_sigmasks_simple() -> None:
        proc = pypsutil.Process()

        sigmasks = proc.sigmasks()

        assert signal.SIGINT in sigmasks.caught

        check_sigmasks(sigmasks)

    def test_sigmasks_set() -> None:
        proc = pypsutil.Process()

        # Mask SIGUSR1
        old_mask = signal.pthread_sigmask(signal.SIG_BLOCK, [signal.SIGUSR1])
        # Ignore SIGUSR2
        signal.signal(signal.SIGUSR2, signal.SIG_IGN)

        sent_sigusr1 = False

        try:
            sigmasks = proc.sigmasks()
            # Make sure it matches the information we get
            check_sigmasks(sigmasks)

            # SIGUSR1 is blocked but not pending
            if hasattr(sigmasks, "blocked"):
                assert signal.SIGUSR1 in sigmasks.blocked
            if hasattr(sigmasks, "pending"):
                assert signal.SIGUSR1 not in sigmasks.pending
            assert signal.SIGUSR1 not in sigmasks.caught
            assert signal.SIGUSR1 not in sigmasks.ignored

            # SIGUSR2 is ignored
            if hasattr(sigmasks, "blocked"):
                assert signal.SIGUSR2 not in sigmasks.blocked
            if hasattr(sigmasks, "pending"):
                assert signal.SIGUSR2 not in sigmasks.pending
            assert signal.SIGUSR2 not in sigmasks.caught
            assert signal.SIGUSR2 in sigmasks.ignored

            # Now we send ourselves SIGUSR1, set a handler for SIGUSR2,
            # and check that everything matches again.

            # Signal handling across threads differs by platform.
            if sys.platform.startswith("linux"):
                signal.pthread_kill(threading.get_ident(), signal.SIGUSR1)
            else:
                os.kill(os.getpid(), signal.SIGUSR1)
            sent_sigusr1 = True

            signal.signal(signal.SIGUSR2, blank_signal_handler)

            sigmasks = proc.sigmasks()
            check_sigmasks(sigmasks)

            # SIGUSR1 is blocked and pending
            if hasattr(sigmasks, "blocked"):
                assert signal.SIGUSR1 in sigmasks.blocked
            if hasattr(sigmasks, "pending"):
                assert signal.SIGUSR1 in sigmasks.pending
            assert signal.SIGUSR1 not in sigmasks.caught
            assert signal.SIGUSR1 not in sigmasks.ignored

            # SIGUSR2 is caught
            if hasattr(sigmasks, "blocked"):
                assert signal.SIGUSR2 not in sigmasks.blocked
            if hasattr(sigmasks, "pending"):
                assert signal.SIGUSR2 not in sigmasks.pending
            assert signal.SIGUSR2 in sigmasks.caught
            assert signal.SIGUSR2 not in sigmasks.ignored

        finally:
            # Cleanup
            if sent_sigusr1:
                signal.sigwait({signal.SIGUSR1})

            signal.pthread_sigmask(signal.SIG_SETMASK, old_mask)
            signal.signal(signal.SIGUSR2, signal.SIG_DFL)

    def test_sigmasks_no_proc() -> None:
        proc = get_dead_process()

        with pytest.raises(pypsutil.NoSuchProcess):
            proc.sigmasks()

        with proc.oneshot():
            with pytest.raises(pypsutil.NoSuchProcess):
                proc.sigmasks()

    def blank_signal_handler(sig: int, frame: Any) -> None:  # pylint: disable=unused-argument
        pass

    def check_sigmasks(sigmasks: pypsutil.ProcessSignalMasks) -> None:
        if hasattr(sigmasks, "blocked"):
            assert sigmasks.blocked == signal.pthread_sigmask(signal.SIG_BLOCK, [])

        if hasattr(sigmasks, "pending"):
            assert sigmasks.pending == signal.sigpending()
