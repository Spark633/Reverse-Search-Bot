"""SauceNAO – beste Quelle für gezeichnete Bilder (Pixiv, Booru-Seiten, e621, FA, Doujins …)."""
from __future__ import annotations

import re
from urllib.parse import quote_plus

import httpx

from bot.models import EngineResult, Match

API_URL = "https://saucenao.com/search.php"
ENGINE = "SauceNAO"

# Indizes mit überwiegend NSFW-Inhalten
_NSFW_INDEXES = {18, 38, 29}  # H-Misc (nhentai), H-Misc (E-Hentai), e621


def _first(value) -> str | None:
    if isinstance(value, list):
        value = ", ".join(str(v) for v in value if v)
    return str(value).strip() or None if value else None


def _parse(payload: dict) -> list[Match]:
    matches: list[Match] = []
    for result in payload.get("results") or []:
        header = result.get("header", {})
        data = result.get("data", {})
        try:
            similarity = float(header.get("similarity", 0))
        except (TypeError, ValueError):
            continue

        urls: list[str] = list(data.get("ext_urls") or [])
        source = data.get("source")
        if isinstance(source, str) and re.match(r"https?://", source) and source not in urls:
            urls.append(source)

        title = _first(data.get("title") or data.get("eng_name") or data.get("jp_name") or data.get("material"))
        author = _first(
            data.get("member_name")
            or data.get("author_name")
            or data.get("creator")
            or data.get("artist")
            or data.get("twitter_user_handle")
        )
        index_id = header.get("index_id")

        if not urls:
            # Doujin-Treffer (nhentai / E-Hentai) liefern oft keine URL, nur den Titel.
            name = title or (source if isinstance(source, str) else None)
            if not name:
                continue
            if index_id == 38:
                urls = [f"https://e-hentai.org/?f_search={quote_plus(name)}"]
            else:
                urls = [f"https://nhentai.net/search/?q={quote_plus(name)}"]

        matches.append(
            Match(
                url=urls[0],
                similarity=similarity,
                engine=ENGINE,
                title=title,
                author=author,
                nsfw=True if index_id in _NSFW_INDEXES else None,
                extra_urls=urls[1:],
            )
        )
    return matches


async def search_saucenao(client: httpx.AsyncClient, image: bytes, api_key: str) -> EngineResult:
    params = {"output_type": 2, "api_key": api_key, "db": 999, "numres": 16, "hide": 0}
    resp = await client.post(API_URL, params=params, files={"file": ("image.jpg", image, "image/jpeg")})

    if resp.status_code == 429:
        return EngineResult(ENGINE, error="Rate-Limit erreicht (zu viele Suchen, später erneut versuchen)")
    if resp.status_code == 403:
        return EngineResult(ENGINE, error="API-Key ungültig")
    resp.raise_for_status()

    payload = resp.json()
    header = payload.get("header", {})
    status = header.get("status", 0)
    if status and status != 0 and not payload.get("results"):
        return EngineResult(ENGINE, error=header.get("message") or f"Status {status}")

    note = None
    remaining = header.get("long_remaining")
    if isinstance(remaining, int) and remaining <= 10:
        note = f"nur noch {remaining} Suchen heute"
    return EngineResult(ENGINE, matches=_parse(payload), note=note)
