from ._detect import _psimpl


def boot_time() -> float:
    return _psimpl.boot_time()


def time_since_boot() -> float:
    return _psimpl.time_since_boot()


if hasattr(_psimpl, "uptime"):

    def uptime() -> float:
        return _psimpl.uptime()
