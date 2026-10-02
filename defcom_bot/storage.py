from __future__ import annotations

import json
from typing import Any

from .config import settings


def data_path(name: str):
    path = settings.state_dir / name
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def load_json(name: str, default: Any = None) -> Any:
    try:
        return json.loads(data_path(name).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def save_json(name: str, value: Any) -> None:
    data_path(name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
