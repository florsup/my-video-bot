import os
import asyncio
import yt_dlp
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

TOKEN = "6283847233:AAFWu8m6BDNLQBh7pgx8rWe5S41Ybnf0UXs"

def download_logic(url: str, msg_id: int) -> str:
    outtmpl = f"video_{msg_id}.%(ext)s"
    
    ydl_opts = {
        # Для Инсты запрашиваем самый лучший доступный формат (обычно это готовый вертикальный mp4)
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': outtmpl,
        'merge_output_format': 'mp4',
        'prefer_ffmpeg': True,
        'geo_bypass': True,
        'nocheckcertificate': True,
        'quiet': True,
        
        # Обязательно подтягиваем файл куки для Инстаграма
        'cookiefile': 'instagram_cookies.txt',
        
        # Жесткая маскировка под реальный мобильный браузер, чтобы Инста не забанила сервер
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9',
            'Origin': 'https://www.instagram.com',
            'Referer': 'https://www.instagram.com/',
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
    
    if "instagram.com" not in url:
        await update.message.reply_text("❌ Отправь корректную ссылку на Instagram Reels или Post")
        return
    
    status_msg = await update.message.reply_text("⏳ Скачиваю видео из Instagram в полном качестве...")
    
    try:
        filename = await asyncio.to_thread(download_logic, url, msg_id)
        
        if not os.path.exists(filename):
            filename = f"video_{msg_id}.mp4"
            
        if not os.path.exists(filename):
            raise FileNotFoundError("Файл не найден. Проверь куки Инстаграма.")
            
        size = os.path.getsize(filename)
        if size > 50 * 1024 * 1024:
            await status_msg.edit_text("❌ Видео весит больше 50MB. Telegram не пропустит такой файл.")
            os.remove(filename)
            return
        
        await status_msg.edit_text("✅ Готово! Отправляю вертикальное видео...")
        
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
        await status_msg.edit_text(f"❌ Ошибка Инстаграма: {str(e)}")
        possible_file = f"video_{msg_id}.mp4"
        if os.path.exists(possible_file):
            os.remove(possible_file)

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_video))
    
