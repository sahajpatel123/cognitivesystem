import os
import sys

try:
    from backend.app.main import app
except ModuleNotFoundError as exc:
    if str(exc) != "No module named 'backend'":
        raise
    _repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
    if _repo_root not in sys.path:
        sys.path.insert(0, _repo_root)
    from backend.app.main import app
