import io

import httpx
from PIL import Image

from bot.config import Config
from bot.engines.fluffle import _parse as parse_fluffle
from bot.engines.iqdb import _parse as parse_iqdb
from bot.engines.saucenao import _parse as parse_saucenao
from bot.formatting import build_keyboard, format_report
from bot.imaging import prepare
from bot.models import EngineResult, Match
from bot.search import merge, reverse_search

IQDB_HTML = """
<html><body><div id='pages' class="pages">
<div><table><tr><th>Your image</th></tr><tr><td class='image'><img src='/thu/x.jpg'></td></tr>
<tr><td>800×600 JPEG</td></tr></table></div>
<div><table><tr><th>Best match</th></tr>
<tr><td class='image'><a href="//danbooru.donmai.us/posts/123"><img src='/danbooru/a.jpg' alt="Rating: e"></a></td></tr>
<tr><td><img class="service-icon" src="/icon/danbooru.ico">Danbooru
<img class="service-icon" src="/icon/gelbooru.ico"><a href="https://gelbooru.com/index.php?page=post&amp;s=view&amp;id=9">Gelbooru</a></td></tr>
<tr><td>1200×900 [Explicit]</td></tr><tr><td>94% similarity</td></tr></table></div>
<div><table><tr><th>No relevant matches</th></tr></table></div>
<div><table><tr><th>Possible match</th></tr>
<tr><td class='image'><a href="https://yande.re/post/show/5"><img src='/y.jpg'></a></td></tr>
<tr><td>yande.re</td></tr><tr><td>500×500 [Safe]</td></tr><tr><td>41% similarity</td></tr></table></div>
</div></body></html>
"""

SAUCE_JSON = {
    "header": {"status": 0, "long_remaining": 99},
    "results": [
        {
            "header": {"similarity": "96.5", "index_id": 5, "index_name": "Index #5: Pixiv"},
            "data": {"ext_urls": ["https://www.pixiv.net/artworks/111"], "title": "Bild", "member_name": "Artist"},
        },
        {
            "header": {"similarity": "92.1", "index_id": 9, "index_name": "Index #9: Danbooru"},
            "data": {
                "ext_urls": ["https://danbooru.donmai.us/post/show/123"],
                "creator": ["a", "b"],
                "source": "https://twitter.com/x/status/1",
            },
        },
        {
            "header": {"similarity": "88", "index_id": 18, "index_name": "Index #18: H-Misc"},
            "data": {"source": "Some Doujin", "eng_name": "[Circle] Some Doujin", "creator": ["c"]},
        },
        {"header": {"similarity": "20", "index_id": 5}, "data": {"ext_urls": ["https://www.pixiv.net/artworks/222"]}},
    ],
}

FLUFFLE_JSON = {
    "results": [
        {"location": "https://e621.net/posts/1", "score": 0.97, "match": "exact", "isSfw": False,
         "platform": "e621", "credits": [{"id": 1, "name": "furartist"}]},
        {"location": "https://www.furaffinity.net/view/2", "score": 0.3, "match": "unlikely", "isSfw": True},
    ]
}


def test_iqdb_parse():
    matches = parse_iqdb(IQDB_HTML)
    assert [m.url for m in matches] == ["https://danbooru.donmai.us/posts/123", "https://yande.re/post/show/5"]
    assert matches[0].similarity == 94
    assert matches[0].nsfw is True
    assert matches[0].extra_urls == ["https://gelbooru.com/index.php?page=post&s=view&id=9"]
    assert matches[1].nsfw is False


def test_saucenao_parse():
    matches = parse_saucenao(SAUCE_JSON)
    assert matches[0].site == "Pixiv" and matches[0].author == "Artist"
    assert matches[1].author == "a, b"
    assert matches[1].extra_urls == ["https://twitter.com/x/status/1"]
    assert matches[2].url.startswith("https://nhentai.net/search/?q=") and matches[2].nsfw is True


def test_fluffle_parse():
    matches = parse_fluffle(FLUFFLE_JSON)
    assert len(matches) == 1
    assert matches[0].similarity == 97 and matches[0].nsfw is True and matches[0].author == "furartist"


def test_merge_dedupes_across_engines():
    a = EngineResult("SauceNAO", [Match("https://danbooru.donmai.us/posts/123", 92, "SauceNAO", author="x")])
    b = EngineResult("IQDB", [Match("http://danbooru.donmai.us/posts/123/", 94, "IQDB", nsfw=True),
                              Match("https://yande.re/post/show/5", 41, "IQDB")])
    matches, hidden = merge([a, b], 60, 8)
    assert len(matches) == 1 and hidden == 1
    assert matches[0].similarity == 94 and matches[0].author == "x" and matches[0].nsfw is True
    assert matches[0].engine == "IQDB + SauceNAO"


def _png(mode="RGBA", size=(3000, 1500)):
    buf = io.BytesIO()
    Image.new(mode, size, (255, 0, 0, 128) if mode == "RGBA" else (1, 2, 3)).save(buf, "PNG")
    return buf.getvalue()


def test_prepare_sizes():
    big, small = prepare(_png())
    assert Image.open(io.BytesIO(big)).size == (2000, 1000)
    assert min(Image.open(io.BytesIO(small)).size) == 256


async def test_full_search_with_mock_transport():
    def handler(request: httpx.Request) -> httpx.Response:
        host = request.url.host
        if host == "saucenao.com":
            return httpx.Response(200, json=SAUCE_JSON)
        if host == "iqdb.org":
            return httpx.Response(200, text=IQDB_HTML)
        if host == "api.fluffle.xyz":
            return httpx.Response(500)
        if host == "litterbox.catbox.moe":
            return httpx.Response(200, text="https://litter.catbox.moe/abc.jpg")
        return httpx.Response(404)

    config = Config("t", "key", frozenset(), 60, 8, True, True, True, "litterbox", "ua")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        report = await reverse_search(client, config, _png("RGB", (600, 400)))

    urls = [m.url for m in report.matches]
    assert urls[0] == "https://www.pixiv.net/artworks/111"
    assert "https://danbooru.donmai.us/posts/123" in urls or "https://danbooru.donmai.us/post/show/123" in urls
    assert any(e.engine == "Fluffle" and e.error == "HTTP 500" for e in report.engines)
    assert report.public_url == "https://litter.catbox.moe/abc.jpg"

    text = format_report(report)
    assert "Pixiv" in text and "Fluffle: HTTP 500" in text
    keyboard = build_keyboard(report)
    assert keyboard is not None and "litter.catbox.moe" in keyboard.inline_keyboard[0][0].url
