import os
import yt_dlp
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

TOKEN = "6283847233:AAFWu8m6BDNLQBh7pgx8rWe5S41Ybnf0UXs"

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
   url = update.message.text
   
   if not any(x in url for x in ["youtube.com", "youtu.be", "tiktok.com", "instagram.com"]):
       await update.message.reply_text("❌ Отправь ссылку с YouTube, TikTok или Instagram")
       return
   
   await update.message.reply_text("⏳ Скачиваю видео в высоком качестве, подожди...")
   
   try:
       ydl_opts = {
           'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best',
           'outtmpl': 'video.%(ext)s',
           'merge_output_format': 'mp4',
           'cookiefile': 'www.youtube.com_cookies.txt',
           'postprocessors': [{
               'key': 'FFmpegVideoConvertor',
               'preferedformat': 'mp4',
           }],
           'prefer_ffmpeg': True,
           'geo_bypass': True,
           'nocheckcertificate': True,
       }
       with yt_dlp.YoutubeDL(ydl_opts) as ydl:
           info = ydl.extract_info(url, download=True)
           filename = f"video.{info['ext']}"
       
       size = os.path.getsize(filename)
       if size > 50 * 1024 * 1024:
           await update.message.reply_text("❌ Видео слишком большое (больше 50MB), попробуй короткое видео")
           os.remove(filename)
           return
       
       await update.message.reply_text("✅ Готово! Отправляю...")
       with open(filename, 'rb') as f:
           await update.message.reply_video(f)
       os.remove(filename)
       
   except Exception as e:
       await update.message.reply_text(f"❌ Ошибка: {str(e)}")

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_video))
app.run_polling()
