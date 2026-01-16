import os
import sys

import mci_backend

if os.environ.get("MCI_BACKEND_MAIN_DEBUG_PRINTED") != "1":
    os.environ["MCI_BACKEND_MAIN_DEBUG_PRINTED"] = "1"
    print("MCI_BACKEND_DEBUG_CWD", os.getcwd())
    print("MCI_BACKEND_DEBUG_SYS_PATH", sys.path[:5])
    print("MCI_BACKEND_DEBUG_PACKAGE_FILE", getattr(mci_backend, "__file__", None))


try:
    from backend.app.main import app
except ModuleNotFoundError as exc:
    if str(exc) != "No module named 'backend'":
        raise
    _repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    if _repo_root not in sys.path:
        sys.path.insert(0, _repo_root)
    from backend.app.main import app
