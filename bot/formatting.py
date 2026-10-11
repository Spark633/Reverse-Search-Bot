from __future__ import annotations

from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from bot.models import Match, site_name
from bot.search import SearchReport

MAX_EXTRA_LINKS = 3


def _short(text: str, limit: int = 80) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _sim_icon(similarity: float) -> str:
    if similarity >= 90:
        return "🟢"
    if similarity >= 75:
        return "🟡"
    return "🟠"


def _format_match(match: Match) -> str:
    rating = " 🔞" if match.nsfw else ""
    head = (
        f'{_sim_icon(match.similarity)} <b>{match.similarity:.0f}%</b> · '
        f'<a href="{escape(match.url, quote=True)}">{escape(match.site)}</a>{rating}'
    )
    lines = [head]
    details = []
    if match.title:
        details.append(f"„{escape(_short(match.title))}“")
    if match.author:
        details.append(f"von {escape(_short(match.author, 50))}")
    if details:
        lines.append("    " + " ".join(details))
    if match.extra_urls:
        extras = " · ".join(
            f'<a href="{escape(u, quote=True)}">{escape(site_name(u))}</a>' for u in match.extra_urls[:MAX_EXTRA_LINKS]
        )
        lines.append(f"    auch: {extras}")
    lines.append(f"    <i>via {escape(match.engine)}</i>")
    return "\n".join(lines)


def format_report(report: SearchReport) -> str:
    parts: list[str] = []
    if report.matches:
        parts.append(f"<b>🔍 {len(report.matches)} Quelle(n) gefunden</b>\n")
        parts.extend(_format_match(m) for m in report.matches)
    else:
        parts.append("<b>😕 Keine sicheren Treffer gefunden.</b>")
        if report.links:
            parts.append("Probier die Buttons unten für weitere Suchmaschinen.")

    if report.hidden_count:
        parts.append(f"\n<i>{report.hidden_count} unsichere(r) Treffer ausgeblendet.</i>")

    status = []
    for engine in report.engines:
        if engine.error:
            status.append(f"⚠️ {escape(engine.engine)}: {escape(engine.error)}")
        elif engine.note:
            status.append(f"ℹ️ {escape(engine.engine)}: {escape(engine.note)}")
    if status:
        parts.append("\n" + "\n".join(status))

    text = "\n".join(parts)
    return text if len(text) <= 4000 else text[:3990] + "…"


def build_keyboard(report: SearchReport) -> InlineKeyboardMarkup | None:
    if not report.links:
        return None
    buttons = [InlineKeyboardButton(name, url=url) for name, url in report.links]
    rows = [buttons[i : i + 3] for i in range(0, len(buttons), 3)]
    return InlineKeyboardMarkup(rows)
