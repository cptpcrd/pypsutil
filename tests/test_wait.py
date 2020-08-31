import signal
import sys
import time

import pypsutil

from .util import managed_child_process


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
        gchild_proc.terminate()
        child_proc.terminate()

        # Wait for both of them to die
        gone, alive = pypsutil.wait_procs([child_proc, gchild_proc])
        assert not alive
        assert set(gone) == {child_proc, gchild_proc}
        assert child_proc.returncode == -signal.SIGTERM  # type: ignore  # pylint: disable=no-member
        assert gchild_proc.returncode is None  # type: ignore

        # Waiting for them again has no effect
        gone, alive = pypsutil.wait_procs([child_proc, gchild_proc])
        assert not alive
        assert set(gone) == {child_proc, gchild_proc}
        assert child_proc.returncode == -signal.SIGTERM  # type: ignore  # pylint: disable=no-member
        assert gchild_proc.returncode is None  # type: ignore
