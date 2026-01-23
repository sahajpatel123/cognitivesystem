import sys
import types


if "jose" not in sys.modules:
    jose_stub = types.ModuleType("jose")
    jose_stub.jwt = types.SimpleNamespace()
    sys.modules["jose"] = jose_stub

if "jose.exceptions" not in sys.modules:
    exceptions_stub = types.ModuleType("jose.exceptions")
    exceptions_stub.JWTError = Exception
    sys.modules["jose.exceptions"] = exceptions_stub

import backend.app.main as m  # noqa: E402


def test_datetime_import_available():
    # Guard against NameError in /api/chat logging
    assert hasattr(m, "datetime")
