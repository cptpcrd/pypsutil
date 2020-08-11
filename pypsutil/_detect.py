import sys

if sys.platform.startswith("linux"):
    from . import _pslinux

    _psimpl = _pslinux
elif sys.platform.startswith("freebsd"):
    from . import _psfreebsd

    _psimpl = _psfreebsd
elif sys.platform.startswith("netbsd"):
    from . import _psnetbsd

    _psimpl = _psnetbsd
elif sys.platform.startswith("openbsd"):
    from . import _psopenbsd

    _psimpl = _psopenbsd
elif sys.platform.startswith("darwin"):
    from . import _psmacosx

    _psimpl = _psmacosx
else:
    _psimpl = None
