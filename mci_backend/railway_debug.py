import os
import sys
from typing import List


def _print_header(title: str) -> None:
    print(f"\n=== {title} ===")


def _safe_listdir(path: str) -> List[str]:
    try:
        return sorted(os.listdir(path))
    except Exception as exc:  # pragma: no cover - diagnostic only
        return [f"<error: {exc}>"]


def _exists(path: str) -> bool:
    return os.path.isdir(path)


def _try_imports() -> None:
    try:
        import backend  # type: ignore # noqa: F401
        import backend.app  # type: ignore # noqa: F401
        from backend.app.main import app  # noqa: F401
        print("IMPORT_OK")
    except Exception as exc:  # pragma: no cover - diagnostic only
        print(f"IMPORT_FAIL: {exc}")


def main() -> None:
    _print_header("CWD")
    print(os.getcwd())

    _print_header("sys.path")
    for entry in sys.path:
        print(entry)

    _print_header("listdir('.') ")
    for entry in _safe_listdir("."):
        print(entry)

    if os.path.exists("/app"):
        _print_header("listdir('/app')")
        for entry in _safe_listdir("/app"):
            print(entry)

    _print_header("dir existence checks")
    for name in ("backend", os.path.join("backend", "app"), "mci_backend"):
        print(f"{name}: {_exists(name)}")

    _print_header("import attempts")
    _try_imports()


if __name__ == "__main__":
    main()
