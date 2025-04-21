import os
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Загружаем переменные окружения из .env файла
load_dotenv()

# Получаем токены из переменных окружения
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
YANDEX_DISK_TOKEN = os.getenv('YANDEX_DISK_TOKEN')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Привет! Напиши мне запрос для поиска фотографий на Яндекс.Диске.')

def search_photos(query: str):
    headers = {
        'Authorization': f'OAuth {YANDEX_DISK_TOKEN}',
    }
    url = 'https://cloud-api.yandex.net/v1/disk/resources/search'
    params = {
        'query': query,
        'media_type': 'image',
    }
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json().get('items', [])
    else:
        return []

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.message.text
    photos = search_photos(query)

    if photos:
        for photo in photos:
            await update.message.reply_text(photo['file'] + '\n')  # Отправляем ссылку на фото
    else:
        await update.message.reply_text('Ничего не найдено.')

def main():
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling()

if __name__ == '__main__':
    main()
