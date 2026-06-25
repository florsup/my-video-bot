import os
import asyncio
import yt_dlp
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

TOKEN = "6283847233:AAFWu8m6BDNLQBh7pgx8rWe5S41Ybnf0UXs"

def download_logic(url: str, msg_id: int) -> str:
    outtmpl = f"video_{msg_id}.%(ext)s"
    
    ydl_opts = {
        # Принудительно ищем вертикальный оригинал (mp4) и лучший звук (m4a)
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': outtmpl,
        'merge_output_format': 'mp4',
        'prefer_ffmpeg': True,
        'geo_bypass': True,
        'nocheckcertificate': True,
        'quiet': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios'],
                'po_token': ['web+1']
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        }
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        
        if not filename.endswith('.mp4'):
            base_path = os.path.splitext(filename)[0]
            if os.path.exists(f"{base_path}.mp4"):
                filename = f"{base_path}.mp4"
                
        return filename

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    msg_id = update.message.message_id
    
    if not any(x in url for x in ["youtube.com", "youtu.be", "tiktok.com", "instagram.com"]):
        await update.message.reply_text("❌ Отправь корректную ссылку на YouTube, TikTok или Instagram")
        return
    
    status_msg = await update.message.reply_text("⏳ Запускаю загрузку в максимальном качестве, подожди...")
    
    try:
        filename = await asyncio.to_thread(download_logic, url, msg_id)
        
        if not os.path.exists(filename):
            filename = f"video_{msg_id}.mp4"
            
        if not os.path.exists(filename):
            raise FileNotFoundError("Скачанный файл не был найден на сервере.")
            
        size = os.path.getsize(filename)
        if size > 50 * 1024 * 1024:
            await status_msg.edit_text("❌ Файл весит больше 50MB. Telegram запрещает ботам отправлять такие тяжелые файлы.")
            os.remove(filename)
            return
        
        await status_msg.edit_text("✅ Скачивание завершено! Загружаю видео в чат...")
        
        with open(filename, 'rb') as f:
            await update.message.reply_video(
                video=f, 
                supports_streaming=True,
                read_timeout=60,
                write_timeout=60
            )
            
        os.remove(filename)
        await status_msg.delete()
        
    except Exception as e:
        await status_msg.edit_text(f"❌ Ошибка при обработке: {str(e)}")
        possible_file = f"video_{msg_id}.mp4"
        if os.path.exists(possible_file):
            os.remove(possible_file)

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_video))
    
    print("🚀 Бот успешно запущен и готов качать!")
    app.run_polling()
