from __future__ import annotations

import logging
import re

import httpx
from telegram import Message, Update
from telegram.constants import ChatAction, ChatType, ParseMode
from telegram.ext import ContextTypes

from bot.config import Config
from bot.formatting import build_keyboard, format_report
from bot.imaging import InvalidImage
from bot.search import reverse_search

log = logging.getLogger(__name__)

MAX_DOWNLOAD = 20 * 1024 * 1024  # Telegram-Bot-API-Limit
URL_RE = re.compile(r"https?://\S+", re.I)

HELP_TEXT = (
    "<b>Reverse-Image-Search-Bot</b>\n\n"
    "Schick mir ein Bild (als Foto oder – für beste Ergebnisse – als <i>Datei</i>), "
    "einen Sticker, ein GIF oder einen Bild-Link, und ich suche die Quelle.\n\n"
    "<b>Durchsuchte Dienste:</b>\n"
    "• SauceNAO – Pixiv, Danbooru, Gelbooru, e621, FurAffinity, DeviantArt, Twitter, nhentai, E-Hentai, Anime/Manga …\n"
    "• IQDB – Danbooru, Gelbooru, yande.re, Konachan, Sankaku, Zerochan …\n"
    "• Fluffle – Furry-Art (e621, FurAffinity, Weasyl, Inkbunny …)\n\n"
    "Über die Buttons kannst du zusätzlich Google Lens, Yandex, Bing, TinEye, ascii2d und trace.moe "
    "öffnen – damit findest du auch Fotos und andere SFW-Bilder.\n\n"
    "<b>In Gruppen:</b> auf ein Bild mit /sauce antworten.\n\n"
    "Tipp: Ausschnitte, Screenshots mit Rändern oder stark bearbeitete Bilder liefern schlechtere Treffer."
)


def _config(context: ContextTypes.DEFAULT_TYPE) -> Config:
    return context.bot_data["config"]


def _allowed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    allowed = _config(context).allowed_user_ids
    user = update.effective_user
    return not allowed or (user is not None and user.id in allowed)


async def _deny(update: Update) -> None:
    user = update.effective_user
    if update.effective_chat and update.effective_chat.type == ChatType.PRIVATE:
        await update.effective_message.reply_text(
            f"⛔ Du darfst diesen Bot nicht benutzen. (Deine ID: {user.id if user else '?'})"
        )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update, context):
        await _deny(update)
        return
    await update.effective_message.reply_text(HELP_TEXT, parse_mode=ParseMode.HTML)


def _file_id(message: Message) -> str | None:
    """Sucht das beste Bild in einer Nachricht."""
    if message.photo:
        return message.photo[-1].file_id
    doc = message.document
    if doc:
        if doc.mime_type and doc.mime_type.startswith("image/"):
            return doc.file_id
        if doc.thumbnail:
            return doc.thumbnail.file_id
    if message.sticker:
        sticker = message.sticker
        if not sticker.is_animated and not sticker.is_video:
            return sticker.file_id
        return sticker.thumbnail.file_id if sticker.thumbnail else None
    for media in (message.animation, message.video, message.video_note):
        if media and media.thumbnail:
            return media.thumbnail.file_id
    return None


async def _download_url(client: httpx.AsyncClient, url: str) -> bytes:
    async with client.stream("GET", url, follow_redirects=True) as resp:
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")
        if not content_type.startswith("image/"):
            raise InvalidImage(f"Link ist kein Bild ({content_type or 'unbekannter Typ'})")
        chunks, size = [], 0
        async for chunk in resp.aiter_bytes():
            size += len(chunk)
            if size > MAX_DOWNLOAD:
                raise InvalidImage("Bild ist größer als 20 MB")
            chunks.append(chunk)
    return b"".join(chunks)


async def _load_image(message: Message, context: ContextTypes.DEFAULT_TYPE) -> bytes | None:
    file_id = _file_id(message)
    if file_id:
        tg_file = await context.bot.get_file(file_id)
        return bytes(await tg_file.download_as_bytearray())

    text = message.text or message.caption or ""
    match = URL_RE.search(text)
    if match:
        return await _download_url(context.bot_data["http"], match.group(0))
    return None


async def _run(update: Update, context: ContextTypes.DEFAULT_TYPE, source: Message) -> None:
    reply_to = update.effective_message
    status = await reply_to.reply_text("🔎 Suche läuft …")
    await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    try:
        data = await _load_image(source, context)
        if data is None:
            await status.edit_text("Ich habe kein Bild gefunden. Schick mir ein Foto, eine Bilddatei oder einen Bild-Link.")
            return
        report = await reverse_search(context.bot_data["http"], _config(context), data)
    except InvalidImage as exc:
        await status.edit_text(f"❌ Bild konnte nicht gelesen werden: {exc}")
        return
    except Exception:
        log.exception("Suche fehlgeschlagen")
        await status.edit_text("❌ Bei der Suche ist ein Fehler aufgetreten.")
        return

    await status.edit_text(
        format_report(report),
        parse_mode=ParseMode.HTML,
        reply_markup=build_keyboard(report),
        disable_web_page_preview=True,
    )


async def on_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Bilder/Links im Privatchat."""
    if not _allowed(update, context):
        await _deny(update)
        return
    await _run(update, context, update.effective_message)


async def sauce_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/sauce als Antwort auf ein Bild (oder mit Bild/Link in derselben Nachricht)."""
    if not _allowed(update, context):
        await _deny(update)
        return
    message = update.effective_message
    source = message.reply_to_message or message
    if _file_id(source) is None and not URL_RE.search(source.text or source.caption or ""):
        await message.reply_text("Antworte mit /sauce auf ein Bild, oder schick /sauce mit einem Bild-Link.")
        return
    await _run(update, context, source)
