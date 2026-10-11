from __future__ import annotations

import logging

import httpx
from telegram import BotCommand, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from bot.config import Config
from bot.handlers import on_media, sauce_command, start

log = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    config = Config.from_env()
    if not config.saucenao_api_key:
        log.warning("Kein SAUCENAO_API_KEY gesetzt – SauceNAO wird übersprungen.")

    async def post_init(app: Application) -> None:
        app.bot_data["config"] = config
        app.bot_data["http"] = httpx.AsyncClient(
            timeout=httpx.Timeout(30, connect=10),
            headers={"User-Agent": config.user_agent},
            follow_redirects=True,
        )
        await app.bot.set_my_commands(
            [BotCommand("sauce", "Quelle eines Bildes suchen (als Antwort)"), BotCommand("help", "Hilfe")]
        )

    async def post_shutdown(app: Application) -> None:
        client = app.bot_data.get("http")
        if client:
            await client.aclose()

    app = (
        Application.builder()
        .token(config.telegram_token)
        .concurrent_updates(True)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    app.add_handler(CommandHandler(["start", "help"], start))
    app.add_handler(CommandHandler(["sauce", "search", "source"], sauce_command))

    media = (
        filters.PHOTO
        | filters.Document.IMAGE
        | filters.Sticker.ALL
        | filters.ANIMATION
        | filters.VIDEO
        | filters.Entity("url")
        | filters.CaptionEntity("url")
    )
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & media & ~filters.COMMAND, on_media))

    log.info("Bot läuft …")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
