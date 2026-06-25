import os
import asyncio
import yt_dlp
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes


TOKEN = "6283847233:AAFWu8m6BDNLQBh7pgx8rWe5S41Ybnf0UXs"

def download_logic(url: str, msg_id: int) -> str:
    """
    Синхронная функция скачивания. 
    Она запускается в отдельном потоке, чтобы не блокировать весь бот.
    """
    # Уникальный шаблон имени файла для каждого запроса на основе ID сообщения
    outtmpl = f"video_{msg_id}.%(ext)s"
    
    ydl_opts = {
        # Загружает САМОЕ лучшее видео + САМЫЙ лучший звук из доступных
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': outtmpl,
        # Принудительно склеивает аудио и видео дорожки в формат MP4 (нужен установленный FFmpeg!)
        'merge_output_format': 'mp4',
        # Файл с куками должен находиться в одной папке со скриптом
        'cookiefile': 'www.youtube.com_cookies.txt', 
        'prefer_ffmpeg': True,
        'geo_bypass': True,
        'nocheckcertificate': True,
        'quiet': True,  # Отключает тонны технических логов в терминале
        
        # 🔥 Специфические настройки для обхода блокировок YouTube (Имитация мобильных приложений)
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios'],  # Ютуб реже блокирует мобильные запросы
                'po_token': ['web+1']                # Попытка обойти проверку "Proof of Token"
            }
        },
        # Свежие заголовки браузера, чтобы бот выглядел как реальный человек
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        }
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        # Извлекаем информацию и скачиваем медиа
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        
        # Поскольку yt_dlp может записать в переменную .mkv или .webm до склейки,
        # проверяем, создался ли итоговый .mp4 файл
        if not filename.endswith('.mp4'):
            base_path = os.path.splitext(filename)[0]
            if os.path.exists(f"{base_path}.mp4"):
                filename = f"{base_path}.mp4"
                
        return filename

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    msg_id = update.message.message_id
    
    # Фильтруем ссылки, чтобы бот не реагировал на обычный текст
    if not any(x in url for x in ["youtube.com", "youtu.be", "tiktok.com", "instagram.com"]):
        await update.message.reply_text("❌ Отправь корректную ссылку на YouTube, TikTok или Instagram")
        return
    
    # Отправляем сообщение-статус и сохраняем его в переменную
    status_msg = await update.message.reply_text("⏳ Запускаю загрузку в максимальном качестве, подожди...")
    
    try:
        # Магия asyncio.to_thread: запускает тяжелую функцию скачивания в фоне,
        # благодаря чему бот продолжает работать для других пользователей
        filename = await asyncio.to_thread(download_logic, url, msg_id)
        
        # Страховка на случай непредвиденного переименования файла
        if not os.path.exists(filename):
            filename = f"video_{msg_id}.mp4"
            
        if not os.path.exists(filename):
            raise FileNotFoundError("Скачанный файл не был найден на сервере.")
            
        size = os.path.getsize(filename)
        # Лимит Telegram для обычных (бесплатных) ботов — 50 Мегабайт
        if size > 50 * 1024 * 1024:
            await status_msg.edit_text("❌ Файл весит больше 50MB. Telegram запрещает ботам отправлять такие тяжелые файлы.")
            os.remove(filename)
            return
        
        await status_msg.edit_text("✅ Скачивание завершено! Загружаю видео в чат...")
        
        # Отправляем именно как ВИДЕО с поддержкой онлайн-просмотра в плеере
        with open(filename, 'rb') as f:
            await update.message.reply_video(
                video=f, 
                supports_streaming=True,  # Позволяет смотреть видео сразу, не дожидаясь полной загрузки
                read_timeout=60,
                write_timeout=60
            )
            
        # Удаляем локальный файл, чтобы не забивать диск
        os.remove(filename)
        # Удаляем промежуточное сообщение статуса, чтобы не засорять чат
        await status_msg.delete()
        
    except Exception as e:
        await status_msg.edit_text(f"❌ Ошибка при обработке: {str(e)}")
        # Подчищаем остаточные файлы в папке скрипта в случае сбоя
        possible_file = f"video_{msg_id}.mp4"
        if os.path.exists(possible_file):
            os.remove(possible_file)

if name == 'main':
    # Инициализация и запуск Telegram-бота
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_video))
    
    print("🚀 Бот успешно запущен и готов качать!")
    app.run_polling()
