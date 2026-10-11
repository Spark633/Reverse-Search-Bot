"""IQDB – Danbooru, Gelbooru, yande.re, Konachan, Sankaku, Zerochan, E-Shuushuu, Anime-Pictures."""
from __future__ import annotations

import re

import httpx
from bs4 import BeautifulSoup

from bot.models import EngineResult, Match, fix_url

URL = "https://iqdb.org/"
ENGINE = "IQDB"

_SIM_RE = re.compile(r"(\d+(?:\.\d+)?)%\s*similarity", re.I)
_RATING_RE = re.compile(r"\[(Safe|Ero|Explicit|Questionable)\]", re.I)


def _parse(html: str) -> list[Match]:
    soup = BeautifulSoup(html, "html.parser")
    pages = soup.find(id="pages")
    if pages is None:
        return []

    matches: list[Match] = []
    for table in pages.find_all("table"):
        header = table.find("th")
        if header is None:
            continue
        label = header.get_text(strip=True).lower()
        if "your image" in label or "no relevant" in label:
            continue

        text = table.get_text(" ", strip=True)
        sim = _SIM_RE.search(text)
        links = [fix_url(a["href"]) for a in table.find_all("a", href=True)]
        links = [link for link in links if link.startswith("http")]
        if not sim or not links:
            continue

        rating = _RATING_RE.search(text)
        nsfw = None
        if rating:
            nsfw = rating.group(1).lower() != "safe"

        # unique, Reihenfolge erhalten
        unique = list(dict.fromkeys(links))
        matches.append(
            Match(url=unique[0], similarity=float(sim.group(1)), engine=ENGINE, nsfw=nsfw, extra_urls=unique[1:])
        )
    return matches


async def search_iqdb(client: httpx.AsyncClient, image: bytes) -> EngineResult:
    resp = await client.post(
        URL,
        data={"MAX_FILE_SIZE": "8388608"},
        files={"file": ("image.jpg", image, "image/jpeg")},
    )
    resp.raise_for_status()
    return EngineResult(ENGINE, matches=_parse(resp.text))
