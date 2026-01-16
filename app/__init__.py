from importlib import import_module
import sys as _sys

_pkg = import_module("backend.app")
_sys.modules[__name__] = _pkg
