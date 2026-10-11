"""Temporärer öffentlicher Upload, damit Links zu Google Lens, Yandex usw. funktionieren.

Telegram-Datei-URLs enthalten den Bot-Token und dürfen daher nie weitergegeben werden.
"""
from __future__ import annotations

import logging

import httpx

log = logging.getLogger(__name__)

LITTERBOX_URL = "https://litterbox.catbox.moe/resources/internals/api.php"


async def upload(client: httpx.AsyncClient, image: bytes, provider: str) -> str | None:
    if provider != "litterbox":
        return None
    try:
        resp = await client.post(
            LITTERBOX_URL,
            data={"reqtype": "fileupload", "time": "1h"},
            files={"fileToUpload": ("image.jpg", image, "image/jpeg")},
        )
        resp.raise_for_status()
        url = resp.text.strip()
        return url if url.startswith("https://") else None
    except httpx.HTTPError as exc:
        log.warning("Upload fehlgeschlagen: %s", exc)
        return None
