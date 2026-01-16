import os, sys
 
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
_backend_dir = os.path.join(_repo_root, "backend")
 
if os.path.isdir(_backend_dir) and _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)
 
try:
    from backend.app.main import app
except ModuleNotFoundError:
    # fallback if backend isn't a package in runtime
    try:
        from app.main import app
    except Exception as e:
        raise RuntimeError(
            f"Cannot import ASGI app. repo_root={_repo_root}, contents={os.listdir(_repo_root)}"
        ) from e
