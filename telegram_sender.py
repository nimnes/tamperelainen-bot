from telegram import Bot
from telegram.constants import ParseMode

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


async def send_message(text, image_url=None):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set."
        )

    bot = Bot(token=TELEGRAM_BOT_TOKEN)

    # Telegram captions are shorter than normal messages.
    # Keep the full message as a normal message if it is too long.
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
