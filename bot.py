import os
import re
import asyncio
import logging
import tempfile
from pathlib import Path

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import yt_dlp

BOT_TOKEN = "6283847233:AAFWu8m6BDNLQBh7pgx8rWe5S41Ybnf0UXs"

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)
logger = logging.getLogger(name)

SUPPORTED_DOMAINS = re.compile(
    r"(https?://)?(www\.)?(instagram\.com|instagr\.am|tiktok\.com|vm\.tiktok\.com|vt\.tiktok\.com)[^\s]*",
    re.IGNORECASE,
)

def extract_url(text: str) -> str | None:
    match = SUPPORTED_DOMAINS.search(text)
    return match.group(0) if match else None

def download_video(url: str, output_dir: str) -> str:
    ydl_opts = {
        "format": "best[ext=mp4]/best",
        "outtmpl": os.path.join(output_dir, "%(id)s.%(ext)s"),
        "merge_output_format": "mp4",
        "quiet": False,
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                "Version/17.0 Mobile/15E148 Safari/604.1"
            ),
        },
        # "cookiesfrombrowser": ("chrome",),  # раскомментируй если нужны cookies
        # "cookiefile": "cookies.txt",
        "extractor_args": {
            "tiktok": {
                "webpage_download": True,
                "api_hostname": "api22-normal-c-useast2a.tiktokv.com",
            }
        },
        "socket_timeout": 30,
        "retries": 5,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)

    path = Path(filename)
    if not path.exists():
        files = list(Path(output_dir).glob("*.mp4")) + list(Path(output_dir).glob("*.webm"))
        if not files:
            raise FileNotFoundError("Файл не найден после загрузки")
        path = sorted(files, key=os.path.getsize, reverse=True)[0]

    return str(path)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("👋 Отправь ссылку на видео из TikTok или Instagram 🎬")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text or ""
    url = extract_url(text)

    if not url:
        await update.message.reply_text("❌ Не нашёл ссылку на TikTok или Instagram.")
        return

    status_msg = await update.message.reply_text("⏳ Скачиваю...")

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            loop = asyncio.get_event_loop()
            file_path = await loop.run_in_executor(None, download_video, url, tmpdir)

            if os.path.getsize(file_path) > 50 * 1024 * 1024:
                await status_msg.edit_text("⚠️ Файл больше 50 МБ — Telegram не пропустит.")
                return

            await status_msg.edit_text("📤 Отправляю...")
            with open(file_path, "rb") as f:
                await update.message.reply_video(video=f, supports_streaming=True, caption="✅ Готово!")
            await status_msg.delete()

    except yt_dlp.utils.DownloadError as e:
        err = str(e).lower()
        if "login" in err or "private" in err:
            hint = "🔒 Приватное видео — нужны cookies."
        elif "404" in err:
            hint = "🔗 Видео не найдено или удалено."
        elif "429" in err or "rate" in err:
            hint = "⏱️ Слишком много запросов, подожди немного."
        else:
            hint = f"<code>{str(e)[-300:]}</code>"
        await status_msg.edit_text(f"❌ Ошибка скачивания.\n\n{hint}", parse_mode="HTML")

    except Exception as e:
        await status_msg.edit_text(f"❌ Ошибка: <code>{str(e)[:200]}</code>", parse_mode="HTML")

def main() -> None:
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Бот запущен...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if name == "main":
    main()
