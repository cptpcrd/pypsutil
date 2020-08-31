import sys
import time

import pypsutil

from .util import managed_child_process


def test_children() -> None:
    cur_proc = pypsutil.Process()

    # We have no children
    assert cur_proc.children() == []
    assert cur_proc.children(recursive=True) == []

    with managed_child_process(
        [
            sys.executable,
            "-c",
            "import os, sys, time; os.spawnv(os.P_NOWAIT, sys.executable, "
            "[sys.executable, '-c', 'exit()']); time.sleep(100)",
        ]
    ) as child_proc:
        # Now we have only one
        assert cur_proc.children() == [child_proc]

        # Wait for the child to fork()
        while True:
            grandchildren = child_proc.children()
            if grandchildren:
                break

            time.sleep(0.01)

        # Our child only has one child
        assert len(grandchildren) == 1

        # The child process has no grandchildren, so children(recursive=True) should report the same
        # as children()
        assert child_proc.children(recursive=True) == grandchildren

        # Make sure the grandchild gets pulled in by recursive=True
        assert set(cur_proc.children(recursive=True)) == {child_proc, *grandchildren}

    # The context manager will kill and reap the child, and the grandparent will be reparented to
    # PID 1 (which should reap it)

    # So now we have no children
    assert cur_proc.children() == []
    assert cur_proc.children(recursive=True) == []
