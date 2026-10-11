"""Fluffle – Furry-Art (e621, FurAffinity, Weasyl, Inkbunny, Twitter …), inkl. NSFW."""
from __future__ import annotations

import httpx

from bot.models import EngineResult, Match

API_URL = "https://api.fluffle.xyz/v1/search"
ENGINE = "Fluffle"

_GOOD_MATCHES = {"exact", "probable", "tossup"}


def _parse(payload: dict) -> list[Match]:
    matches: list[Match] = []
    for result in payload.get("results") or []:
        url = result.get("location")
        if not url:
            continue
        match_kind = str(result.get("match", "")).lower()
        if match_kind and match_kind not in _GOOD_MATCHES:
            continue
        try:
            score = float(result.get("score", 0)) * 100
        except (TypeError, ValueError):
            continue
        credits = [c.get("name") for c in result.get("credits") or [] if isinstance(c, dict) and c.get("name")]
        is_sfw = result.get("isSfw")
        matches.append(
            Match(
                url=url,
                similarity=score,
                engine=ENGINE,
                author=", ".join(credits) or None,
                nsfw=None if is_sfw is None else not is_sfw,
            )
        )
    return matches


async def search_fluffle(client: httpx.AsyncClient, image: bytes) -> EngineResult:
    resp = await client.post(
        API_URL,
        data={"includeNsfw": "true", "limit": "16"},
        files={"file": ("image.jpg", image, "image/jpeg")},
    )
    if resp.status_code == 429:
        return EngineResult(ENGINE, error="Rate-Limit erreicht")
    resp.raise_for_status()
    return EngineResult(ENGINE, matches=_parse(resp.json()))
