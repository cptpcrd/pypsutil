import pytest

import pypsutil

from .util import get_dead_process

if pypsutil.UNIX:

    def test_priority() -> None:
        proc = pypsutil.Process()

        assert proc.getpriority() == proc.getpriority()

        # Should succeed
        proc.setpriority(proc.getpriority())

    def test_priority_no_proc() -> None:
        proc = get_dead_process()

        with pytest.raises(pypsutil.NoSuchProcess):
            proc.getpriority()

    def test_priority_pid_0() -> None:
        try:
            proc = pypsutil.Process(0)
        except pypsutil.NoSuchProcess:
            pytest.skip("PID 0 does not appear")
        else:
            # If it does, we should be able to get its priority
            prio = proc.getpriority()

            # But not set it
            with pytest.raises(pypsutil.AccessDenied):
                proc.setpriority(prio)

else:

    def test_prioclass() -> None:
        proc = pypsutil.Process()
        proc.setprioclass(proc.getprioclass())

    def test_prioclass_no_proc() -> None:
        proc = get_dead_process()

        with pytest.raises(pypsutil.NoSuchProcess):
            proc.getprioclass()

        with pytest.raises(pypsutil.NoSuchProcess):
            # pylint: disable=no-member
            proc.setprioclass(pypsutil.PriorityClass.NORMAL)  # type: ignore[attr-defined]
