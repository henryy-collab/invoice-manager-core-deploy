from pathlib import Path


def ensure_data_dirs() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    data_root = repo_root / "local" / "data"
    for name in ("incoming", "outgoing", "archive", "logs", "reports", "state"):
        (data_root / name).mkdir(parents=True, exist_ok=True)
