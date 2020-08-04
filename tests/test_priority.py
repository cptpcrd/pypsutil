import pypsutil


def test_priority() -> None:
    proc = pypsutil.Process()

    assert proc.getpriority() == proc.getpriority()

    # Should succeed
    proc.setpriority(proc.getpriority())
