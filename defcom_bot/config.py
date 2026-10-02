from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


@dataclass(frozen=True, slots=True)
class Settings:
    token: str = os.getenv("DISCORD_TOKEN", "")
    guild_id: int = int(os.getenv("GUILD_ID", "0") or 0)
    state_dir: Path = Path(os.getenv("STATE_DIR", "state"))
    log_level: str = os.getenv("LOG_LEVEL", "info").upper()
    def validate(self) -> None:
        missing = []
        if not self.token:
            missing.append("DISCORD_TOKEN")
        if not self.guild_id:
            missing.append("GUILD_ID")
        if missing:
            raise RuntimeError(f"Variáveis ausentes no .env: {', '.join(missing)}. Copie .env.example para .env e preencha.")


settings = Settings()
