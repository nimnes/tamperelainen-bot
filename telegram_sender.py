from telegram import Bot
from telegram.constants import ParseMode

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


async def send_message(text, image_url=None):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set."
        )

    bot = Bot(token=TELEGRAM_BOT_TOKEN)

    # Option A: keep the original article image as the Telegram photo.
    # Telegram may crop the thumbnail/preview in the chat UI, but tapping
    # the preview opens the full photo stored by Telegram.
    #
    # We deliberately do not crop, resize, or create a thumbnail ourselves.
    # This preserves the original aspect ratio and image quality.
    # Telegram captions are shorter than normal messages; if the caption is
    # too long, fall back to a normal text message rather than splitting the
    # article card into separate image/text messages.
    if image_url and len(text) <= 1024:
        await bot.send_photo(
            chat_id=TELEGRAM_CHAT_ID,
            photo=image_url,
            caption=text,
            parse_mode=ParseMode.HTML,
        )
        return

    chunks = [text[i:i + 4000] for i in range(0, len(text), 4000)]

    for chunk in chunks:
        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=chunk,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
