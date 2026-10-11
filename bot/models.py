from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlsplit, urlunsplit

# Hostname-Fragment -> Anzeigename
_SITES = {
    "pixiv.net": "Pixiv",
    "fanbox.cc": "Fanbox",
    "danbooru.donmai.us": "Danbooru",
    "gelbooru.com": "Gelbooru",
    "yande.re": "yande.re",
    "konachan": "Konachan",
    "sankakucomplex.com": "Sankaku",
    "e621.net": "e621",
    "e926.net": "e926",
    "furaffinity.net": "FurAffinity",
    "inkbunny.net": "Inkbunny",
    "weasyl.com": "Weasyl",
    "deviantart.com": "DeviantArt",
    "artstation.com": "ArtStation",
    "twitter.com": "Twitter/X",
    "x.com": "Twitter/X",
    "bsky.app": "Bluesky",
    "nhentai.net": "nhentai",
    "e-hentai.org": "E-Hentai",
    "exhentai.org": "ExHentai",
    "hitomi.la": "Hitomi",
    "kemono.su": "Kemono",
    "kemono.party": "Kemono",
    "patreon.com": "Patreon",
    "skeb.jp": "Skeb",
    "tumblr.com": "Tumblr",
    "newgrounds.com": "Newgrounds",
    "zerochan.net": "Zerochan",
    "e-shuushuu.net": "E-Shuushuu",
    "anime-pictures.net": "Anime-Pictures",
    "rule34.xxx": "Rule34",
    "rule34.paheal.net": "Paheal",
    "hentai-foundry.com": "HentaiFoundry",
    "mangadex.org": "MangaDex",
    "myanimelist.net": "MyAnimeList",
    "anidb.net": "AniDB",
    "anilist.co": "AniList",
    "imdb.com": "IMDb",
    "seiga.nicovideo.jp": "Nico Seiga",
    "nijie.info": "Nijie",
    "drawr.net": "Drawr",
    "fantia.jp": "Fantia",
    "misskey.io": "Misskey",
    "baraag.net": "Baraag",
    "pawoo.net": "Pawoo",
    "fakku.net": "FAKKU",
    "mangaupdates.com": "MangaUpdates",
}


def site_name(url: str) -> str:
    host = urlsplit(url).hostname or ""
    for fragment, name in _SITES.items():
        if host == fragment or host.endswith("." + fragment) or fragment in host:
            return name
    host = host.removeprefix("www.")
    return host or "Link"


def normalize_url(url: str) -> str:
    """Schlüssel zum Deduplizieren (http/https, www, x.com/twitter.com, Slash am Ende)."""
    parts = urlsplit(url.strip())
    host = (parts.hostname or "").removeprefix("www.").removeprefix("mobile.")
    if host == "x.com":
        host = "twitter.com"
    path = parts.path.rstrip("/")
    return urlunsplit(("https", host, path, parts.query, ""))


def fix_url(url: str) -> str:
    url = url.strip()
    if url.startswith("//"):
        return "https:" + url
    return url


@dataclass
class Match:
    url: str
    similarity: float  # 0..100
    engine: str
    title: str | None = None
    author: str | None = None
    nsfw: bool | None = None
    extra_urls: list[str] = field(default_factory=list)

    @property
    def site(self) -> str:
        return site_name(self.url)


@dataclass
class EngineResult:
    engine: str
    matches: list[Match] = field(default_factory=list)
    error: str | None = None
    note: str | None = None
