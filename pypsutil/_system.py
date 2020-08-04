from . import _psimpl


def boot_time() -> float:
    return _psimpl.boot_time()
