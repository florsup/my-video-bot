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

# ─── Настройки ────────────────────────────────────────────────────────────────

BOT_TOKEN = "6283847233:AAFWu8m6BDNLQBh7pgx8rWe5S41Ybnf0UXs"

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─── Вспомогательные функции ──────────────────────────────────────────────────

SUPPORTED_DOMAINS = re.compile(
    r"(https?://)?(www\.)?"
    r"(instagram\.com|instagr\.am|tiktok\.com|vm\.tiktok\.com|vt\.tiktok\.com)"
    r"[^\s]*",
    re.IGNORECASE,
)


def extract_url(text: str) -> str | None:
    """Вытаскивает первую ссылку на Instagram или TikTok из текста."""
    match = SUPPORTED_DOMAINS.search(text)
    return match.group(0) if match else None


def download_video(url: str, output_dir: str) -> str:
    """
    Скачивает видео через yt-dlp и возвращает путь к файлу.
    Качество: лучшее доступное (видео + аудио), mp4.
    """
    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": os.path.join(output_dir, "%(id)s.%(ext)s"),
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        },
        # "cookiesfrombrowser": ("chrome",),  # раскомментируй для приватных инста
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)

    path = Path(filename)
    if not path.exists():
        mp4_files = list(Path(output_dir).glob("*.mp4"))
        if not mp4_files:
            raise FileNotFoundError("Файл не найден после загрузки")
        path = mp4_files[0]

    return str(path)


# ─── Хендлеры ─────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 Привет! Отправь мне ссылку на видео из:\n"
        "• TikTok\n"
        "• Instagram (Reels / пост)\n\n"
        "И я скачаю его для тебя 🎬"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "ℹ️ *Как пользоваться:*\n\n"
        "1. Скопируй ссылку на видео из TikTok или Instagram\n"
        "2. Вставь её сюда и отправь\n"
        "3. Получи видео!\n\n"
        "⚠️ *Примечание:* для скачивания приватных Instagram-видео\n"
        "может потребоваться авторизация (см. README).",
        parse_mode="Markdown",
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text or ""
    url = extract_url(text)

    if not url:
        await update.message.reply_text(
            "❌ Не нашёл ссылку на TikTok или Instagram.\n"
            "Пришли ссылку в формате https://..."
        )
        return

    status_msg = await update.message.reply_text("⏳ Скачиваю видео, подожди...")

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            loop = asyncio.get_event_loop()
            file_path = await loop.run_in_executor(
                None, download_video, url, tmpdir
            )

            file_size = os.path.getsize(file_path)
            max_size = 50 * 1024 * 1024  # Telegram лимит: 50 МБ

            if file_size > max_size:
                await status_msg.edit_text(
                    f"⚠️ Файл слишком большой ({file_size // 1024 // 1024} МБ).\n"
                    "Telegram принимает видео до 50 МБ."
                )
                return

            await status_msg.edit_text("📤 Отправляю видео...")

            with open(file_path, "rb") as video_file:
                await update.message.reply_video(
                    video=video_file,
                    supports_streaming=True,
                    caption="✅ Готово!",
                )

            await status_msg.delete()

    except yt_dlp.utils.DownloadError as e:
        logger.error("DownloadError: %s", e)
        await status_msg.edit_text(
            "❌ Не удалось скачать видео.\n\n"
            "Возможные причины:\n"
            "• Приватный аккаунт\n"
            "• Ссылка устарела или неверная\n"
            "• Сервис временно недоступен"
        )
    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        await status_msg.edit_text("❌ Произошла ошибка. Попробуй позже.")


# ─── Запуск бота ──────────────────────────────────────────────────────────────

def main() -> None:
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Бот запущен...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
