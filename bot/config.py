from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from bot import __version__


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "ja"}


def _int(name: str, default: int) -> int:
    value = os.getenv(name, "").strip()
    return int(value) if value else default


@dataclass(frozen=True)
class Config:
    telegram_token: str
    saucenao_api_key: str | None
    allowed_user_ids: frozenset[int]
    min_similarity: float
    max_results: int
    enable_saucenao: bool
    enable_iqdb: bool
    enable_fluffle: bool
    public_upload: str
    user_agent: str

    @classmethod
    def from_env(cls) -> "Config":
        # einstellungen.txt (einfach unter Windows/Mac zu bearbeiten) oder .env
        for name in ("einstellungen.txt", ".env"):
            path = Path(name)
            if path.is_file():
                load_dotenv(path, encoding="utf-8-sig")
        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        if not token:
            raise SystemExit(
                "TELEGRAM_BOT_TOKEN ist nicht gesetzt. Trag ihn in einstellungen.txt ein "
                "(Vorlage: einstellungen-vorlage.txt) und starte den Bot im selben Ordner."
            )

        allowed = frozenset(
            int(part)
            for part in os.getenv("ALLOWED_USER_IDS", "").replace(" ", "").split(",")
            if part
        )
        contact = os.getenv("CONTACT", "").strip() or "unknown"

        return cls(
            telegram_token=token,
            saucenao_api_key=os.getenv("SAUCENAO_API_KEY", "").strip() or None,
            allowed_user_ids=allowed,
            min_similarity=float(os.getenv("MIN_SIMILARITY", "60") or 60),
            max_results=_int("MAX_RESULTS", 8),
            enable_saucenao=_bool("ENABLE_SAUCENAO", True),
            enable_iqdb=_bool("ENABLE_IQDB", True),
            enable_fluffle=_bool("ENABLE_FLUFFLE", True),
            public_upload=os.getenv("PUBLIC_UPLOAD", "litterbox").strip().lower() or "none",
            user_agent=f"reverse-search-bot/{__version__} (by {contact} on Telegram)",
        )
