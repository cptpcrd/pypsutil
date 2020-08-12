import os
import sys
import time

import pypsutil

from .util import fork_proc


def test_children() -> None:
    cur_proc = pypsutil.Process()
    child_proc = fork_proc(lambda: sys.exit(0))

    assert cur_proc.children() == [child_proc]

    os.waitpid(child_proc.pid, 0)


def test_children_recursive_simple() -> None:
    cur_proc = pypsutil.Process()
    child_proc = fork_proc(lambda: sys.exit(0))

    assert cur_proc.children(recursive=True) == [child_proc]

    os.waitpid(child_proc.pid, 0)


def test_children_recursive_grancdhildren() -> None:
    def child_callback() -> None:
        fork_proc(lambda: sys.exit(0))
        # Don't reap our child (the grandchild of the testing process), so it will still show up
        time.sleep(100)

    cur_proc = pypsutil.Process()
    child_proc = fork_proc(child_callback)

    # Wait for the child to fork()
    while True:
        grandchildren = child_proc.children()
        if grandchildren:
            break

        time.sleep(0.01)

    assert len(grandchildren) == 1

    # Make sure the grandchild gets pulled in by recursive=True
    assert cur_proc.children(recursive=True) == [child_proc, *grandchildren]

    # Kill the child and wait for it.
    # The grandchild should be reparented to (and reaped by) PID 1.
    child_proc.terminate()
    os.waitpid(child_proc.pid, 0)
