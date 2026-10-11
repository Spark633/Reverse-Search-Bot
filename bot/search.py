from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from urllib.parse import quote, quote_plus

import httpx

from bot.config import Config
from bot.engines import search_fluffle, search_iqdb, search_saucenao
from bot.imaging import prepare
from bot.models import EngineResult, Match, normalize_url
from bot.uploader import upload

log = logging.getLogger(__name__)

ENGINE_TIMEOUT = 40


@dataclass
class SearchReport:
    matches: list[Match]
    engines: list[EngineResult]
    public_url: str | None
    hidden_count: int = 0
    links: list[tuple[str, str]] = field(default_factory=list)


def external_links(public_url: str) -> list[tuple[str, str]]:
    enc = quote_plus(public_url)
    return [
        ("SauceNAO", f"https://saucenao.com/search.php?url={enc}"),
        ("ascii2d", f"https://ascii2d.net/search/url/{quote(public_url, safe='')}"),
        ("IQDB", f"https://iqdb.org/?url={enc}"),
        ("Google Lens", f"https://lens.google.com/uploadbyurl?url={enc}"),
        ("Yandex", f"https://yandex.com/images/search?rpt=imageview&url={enc}"),
        ("Bing", f"https://www.bing.com/images/search?view=detailv2&iss=sbi&q=imgurl:{enc}"),
        ("TinEye", f"https://tineye.com/search?url={enc}"),
        ("trace.moe", f"https://trace.moe/?url={enc}"),
    ]


async def _guard(name: str, coro) -> EngineResult:
    try:
        return await asyncio.wait_for(coro, ENGINE_TIMEOUT)
    except asyncio.TimeoutError:
        return EngineResult(name, error="Zeitüberschreitung")
    except httpx.HTTPStatusError as exc:
        return EngineResult(name, error=f"HTTP {exc.response.status_code}")
    except Exception as exc:  # noqa: BLE001 - eine kaputte Engine darf die Suche nicht abbrechen
        log.exception("%s fehlgeschlagen", name)
        return EngineResult(name, error=type(exc).__name__)


def merge(results: list[EngineResult], min_similarity: float, max_results: int) -> tuple[list[Match], int]:
    """Dedupliziert über alle Engines, sortiert nach Ähnlichkeit."""
    best: dict[str, Match] = {}
    for result in results:
        for match in result.matches:
            key = normalize_url(match.url)
            existing = best.get(key)
            if existing is None:
                best[key] = match
                continue
            # Infos zusammenführen, höhere Ähnlichkeit gewinnt
            winner, other = (match, existing) if match.similarity > existing.similarity else (existing, match)
            winner.title = winner.title or other.title
            winner.author = winner.author or other.author
            winner.nsfw = winner.nsfw if winner.nsfw is not None else other.nsfw
            winner.extra_urls = list(dict.fromkeys(winner.extra_urls + other.extra_urls))
            if other.engine not in winner.engine.split(" + "):
                winner.engine = f"{winner.engine} + {other.engine}"
            best[key] = winner

    # Extra-URLs entfernen, die bereits eigene Treffer sind
    keys = set(best)
    for match in best.values():
        match.extra_urls = [u for u in match.extra_urls if normalize_url(u) not in keys]

    ordered = sorted(best.values(), key=lambda m: m.similarity, reverse=True)
    good = [m for m in ordered if m.similarity >= min_similarity]
    hidden = len(ordered) - len(good)
    return good[:max_results], hidden


async def reverse_search(client: httpx.AsyncClient, config: Config, data: bytes) -> SearchReport:
    big, small = await asyncio.to_thread(prepare, data)

    tasks = []
    if config.enable_saucenao and config.saucenao_api_key:
        tasks.append(_guard("SauceNAO", search_saucenao(client, big, config.saucenao_api_key)))
    if config.enable_iqdb:
        tasks.append(_guard("IQDB", search_iqdb(client, big)))
    if config.enable_fluffle:
        tasks.append(_guard("Fluffle", search_fluffle(client, small)))

    upload_task = asyncio.create_task(upload(client, big, config.public_upload))
    results = list(await asyncio.gather(*tasks))
    public_url = await upload_task

    matches, hidden = merge(results, config.min_similarity, config.max_results)
    return SearchReport(
        matches=matches,
        engines=results,
        public_url=public_url,
        hidden_count=hidden,
        links=external_links(public_url) if public_url else [],
    )
