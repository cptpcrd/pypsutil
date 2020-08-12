import signal
import sys
import time

import pypsutil

from .util import managed_child_process, managed_child_process2, unix_only

if pypsutil.UNIX:
    child_sigterm = -signal.SIGTERM
    gchild_sigterm = None
else:
    child_sigterm = signal.SIGTERM
    gchild_sigterm = signal.SIGTERM


@unix_only
def test_wait_procs_basic() -> None:
    with managed_child_process(
        [
            sys.executable,
            "-c",
            "import os, sys, time; os.spawnv(os.P_NOWAIT, sys.executable, "
            "[sys.executable, '-c', 'exit()']); time.sleep(100)",
        ]
    ) as child_proc:
        # Wait for the child to fork()
        while True:
            grandchildren = child_proc.children()
            if grandchildren:
                break

            time.sleep(0.01)

        # Our child only has one child
        assert len(grandchildren) == 1
        gchild_proc = grandchildren[0]

        # Both alive
        gone, alive = pypsutil.wait_procs([child_proc, gchild_proc], timeout=0)
        assert not gone
        assert set(alive) == {child_proc, gchild_proc}
        assert not hasattr(child_proc, "returncode")
        assert not hasattr(gchild_proc, "returncode")

        # Same results if we use a short timeout
        gone, alive = pypsutil.wait_procs([child_proc, gchild_proc], timeout=0.01)
        assert not gone
        assert set(alive) == {child_proc, gchild_proc}
        assert not hasattr(child_proc, "returncode")
        assert not hasattr(gchild_proc, "returncode")

        # Send SIGTERM
        try:
            gchild_proc.terminate()
        except pypsutil.NoSuchProcess:
            pass
        try:
            child_proc.terminate()
        except pypsutil.NoSuchProcess:
            pass

        # Wait for both of them to die
        gone, alive = pypsutil.wait_procs([child_proc, gchild_proc])
        assert not alive
        assert set(gone) == {child_proc, gchild_proc}
        assert child_proc.returncode == child_sigterm  # type: ignore  # pylint: disable=no-member
        assert gchild_proc.returncode == gchild_sigterm  # type: ignore

        # Waiting for them again has no effect
        gone, alive = pypsutil.wait_procs([child_proc, gchild_proc])
        assert not alive
        assert set(gone) == {child_proc, gchild_proc}
        assert child_proc.returncode == child_sigterm  # type: ignore  # pylint: disable=no-member
        assert gchild_proc.returncode == gchild_sigterm  # type: ignore


def test_wait_single_proc() -> None:
    with managed_child_process(
        [
            sys.executable,
            "-c",
            "import os, sys, time; os.spawnv(os.P_NOWAIT, sys.executable, "
            "[sys.executable, '-c', 'exit()']); time.sleep(100)",
        ]
    ) as child_proc:
        # Wait for the child to fork()
        while True:
            grandchildren = child_proc.children()
            if grandchildren:
                break

            time.sleep(0.01)

        # Our child only has one child
        assert len(grandchildren) == 1
        gchild_proc = grandchildren[0]

        # Child is alive
        gone, alive = pypsutil.wait_procs([child_proc], timeout=0)
        assert not gone
        assert set(alive) == {child_proc}
        assert not hasattr(child_proc, "returncode")

        # Grandchild is alive
        gone, alive = pypsutil.wait_procs([gchild_proc], timeout=0)
        assert not gone
        assert set(alive) == {gchild_proc}
        assert not hasattr(gchild_proc, "returncode")

        # Same results if we use a short timeout
        gone, alive = pypsutil.wait_procs([child_proc], timeout=0.01)
        assert not gone
        assert set(alive) == {child_proc}
        assert not hasattr(child_proc, "returncode")

        gone, alive = pypsutil.wait_procs([gchild_proc], timeout=0.01)
        assert not gone
        assert set(alive) == {gchild_proc}
        assert not hasattr(gchild_proc, "returncode")

        # Send SIGTERM
        try:
            gchild_proc.terminate()
        except pypsutil.NoSuchProcess:
            pass
        try:
            child_proc.terminate()
        except pypsutil.NoSuchProcess:
            pass

        # Wait for both of them to die
        # In this order
        gone, alive = pypsutil.wait_procs([gchild_proc])
        assert not alive
        assert set(gone) == {gchild_proc}
        assert gchild_proc.returncode in (gchild_sigterm, None)  # type: ignore

        gone, alive = pypsutil.wait_procs([child_proc])
        assert not alive
        assert set(gone) == {child_proc}
        assert child_proc.returncode == child_sigterm  # type: ignore  # pylint: disable=no-member

        # Waiting for them again has no effect
        gone, alive = pypsutil.wait_procs([child_proc])
        assert not alive
        assert set(gone) == {child_proc}
        assert child_proc.returncode == child_sigterm  # type: ignore  # pylint: disable=no-member

        gone, alive = pypsutil.wait_procs([gchild_proc])
        assert not alive
        assert set(gone) == {gchild_proc}
        assert gchild_proc.returncode in (gchild_sigterm, None)  # type: ignore


def test_wait_single_proc2() -> None:
    with managed_child_process(
        [
            sys.executable,
            "-c",
            "import os, sys, time; os.spawnv(os.P_NOWAIT, sys.executable, "
            "[sys.executable, '-c', 'import time; time.sleep(10)']); time.sleep(100)",
        ]
    ) as child_proc:
        # Wait for the child to fork()
        while True:
            grandchildren = child_proc.children()
            if grandchildren:
                break

            time.sleep(0.01)

        # Our child only has one child
        assert len(grandchildren) == 1
        gchild_proc = grandchildren[0]

        # Send SIGTERM
        try:
            gchild_proc.terminate()
        except pypsutil.NoSuchProcess:
            pass
        try:
            child_proc.terminate()
        except pypsutil.NoSuchProcess:
            pass

        # Wait for both of them to die
        # In this order
        # Set a timeout that isn't 0 or None to test some extra portions of the code
        assert gchild_proc.wait(timeout=0.5) in (gchild_sigterm, None)
        assert child_proc.wait(timeout=0.5) == child_sigterm


def test_wait_single_proc3() -> None:
    with managed_child_process(
        [
            sys.executable,
            "-c",
            "import os, sys, time; os.spawnv(os.P_NOWAIT, sys.executable, "
            "[sys.executable, '-c', 'exit()']); time.sleep(100)",
        ]
    ) as child_proc:
        # Send SIGTERM
        try:
            child_proc.terminate()
        except pypsutil.NoSuchProcess:
            pass

        # Wait for it to become a zombie
        try:
            while child_proc.status() != pypsutil.ProcessStatus.ZOMBIE:
                time.sleep(0.01)
        except pypsutil.NoSuchProcess:
            pass

        # Now wait() for it
        assert child_proc.wait(timeout=0) == child_sigterm

        # Wait again
        assert child_proc.wait(timeout=0) == child_sigterm

        # Same results if we wait again
        gone, alive = pypsutil.wait_procs([child_proc])
        assert not alive
        assert set(gone) == {child_proc}
        assert child_proc.returncode == child_sigterm  # type: ignore # pylint: disable=no-member


@unix_only
def test_wait_procs_callback() -> None:
    with managed_child_process2(
        [
            sys.executable,
            "-c",
            "import os, sys, time; os.spawnv(os.P_NOWAIT, sys.executable, "
            "[sys.executable, '-c', 'exit()']); time.sleep(100)",
        ]
    ) as child_proc:
        # Wait for the child to fork()
        while True:
            grandchildren = child_proc.children()
            if grandchildren:
                break

            time.sleep(0.01)

        # Our child only has one child
        assert len(grandchildren) == 1
        gchild_proc = grandchildren[0]

        # Send SIGTERM
        try:
            gchild_proc.terminate()
        except pypsutil.NoSuchProcess:
            pass
        try:
            child_proc.terminate()
        except pypsutil.NoSuchProcess:
            pass

        procs = {}

        def callback(proc: pypsutil.Process) -> None:
            procs[proc] = proc.returncode  # type: ignore

        gone, alive = pypsutil.wait_procs([child_proc, gchild_proc], callback=callback)
        assert not alive
        assert set(gone) == {child_proc, gchild_proc}
        assert child_proc.returncode == child_sigterm  # pylint: disable=no-member
        assert gchild_proc.returncode == gchild_sigterm  # type: ignore

        assert procs == {child_proc: child_sigterm, gchild_proc: gchild_sigterm}

        procs = {}

        # Same results if we try again
        gone, alive = pypsutil.wait_procs([child_proc, gchild_proc], callback=callback)
        assert not alive
        assert set(gone) == {child_proc, gchild_proc}
        assert child_proc.returncode == child_sigterm  # pylint: disable=no-member
        assert gchild_proc.returncode == gchild_sigterm  # type: ignore

        assert procs == {child_proc: child_sigterm, gchild_proc: gchild_sigterm}


def test_wait_procs_single_callback() -> None:
    with managed_child_process2(
        [
            sys.executable,
            "-c",
            "import time; time.sleep(100)",
        ]
    ) as child_proc:
        # Send SIGTERM
        try:
            child_proc.terminate()
        except pypsutil.NoSuchProcess:
            pass

        procs = {}

        def callback(proc: pypsutil.Process) -> None:
            procs[proc] = proc.returncode  # type: ignore

        gone, alive = pypsutil.wait_procs([child_proc], callback=callback)
        assert not alive
        assert set(gone) == {child_proc}
        assert child_proc.returncode == child_sigterm  # pylint: disable=no-member

        assert procs == {child_proc: child_sigterm}
