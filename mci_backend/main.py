import os
import sys
from typing import List


def _compute_repo_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))


def _ensure_repo_root_on_syspath(repo_root: str) -> None:
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)


def _assert_backend_dir(repo_root: str) -> str:
    backend_dir = os.path.join(repo_root, "backend")
    if not os.path.isdir(backend_dir):
        raise RuntimeError(
            f"backend directory missing; repo_root={repo_root}; "
            f"cwd={os.getcwd()}; sys.path[:3]={_fmt_sys_path(sys.path)}; "
            f"repo_root_contents={_safe_listdir(repo_root)}"
        )
    return backend_dir


def _fmt_sys_path(path_list: List[str]) -> str:
    # Show the first few entries only to keep message concise
    return repr(path_list[:3])


def _safe_listdir(path: str) -> List[str]:
    try:
        return sorted(os.listdir(path))
    except Exception:
        return ["<unavailable>"]


_repo_root = _compute_repo_root()
_ensure_repo_root_on_syspath(_repo_root)
_backend_dir = _assert_backend_dir(_repo_root)

try:
    from backend.app.main import app  # noqa: E402
except ModuleNotFoundError as exc:
    raise RuntimeError(
        f"Cannot import backend.app.main: {exc}; "
        f"repo_root={_repo_root}; cwd={os.getcwd()}; sys.path[:3]={_fmt_sys_path(sys.path)}; "
        f"repo_root_contents={_safe_listdir(_repo_root)}; "
        f"backend_dir={_backend_dir}; backend_dir_contents={_safe_listdir(_backend_dir)}"
    ) from exc
