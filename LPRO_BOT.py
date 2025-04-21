import os
import requests
import logging
from io import BytesIO
from PIL import Image
import pytesseract
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Загружаем переменные окружения из .env файла
load_dotenv()

# Получаем токены из переменных окружения
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
YANDEX_DISK_TOKEN = os.getenv('YANDEX_DISK_TOKEN')

def get_all_files(folder_path=''):
    if folder_path == '':
        folder_path = '/'
    logger.info("Получение файлов из папки: %s", folder_path)
    headers = {
        'Authorization': f'OAuth {YANDEX_DISK_TOKEN}',
    }
    url = 'https://cloud-api.yandex.net/v1/disk/resources/'
    params = {
        'path': folder_path,
        'fields': '_embedded.items.name,_embedded.items.path,_embedded.items.type',
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()  # Вызывает ошибку для плохих ответов
    except requests.exceptions.HTTPError as http_err:
        logger.error("Произошла HTTP ошибка: %s", http_err)
        return []
    except Exception as err:
        logger.error("Произошла ошибка: %s", err)
        return []

    items = response.json().get('_embedded', {}).get('items', [])
    logger.info("Найдено %d файлов в папке %s", len(items), folder_path)
    return items

def get_file_url(file_path):
    headers = {
        'Authorization': f'OAuth {YANDEX_DISK_TOKEN}',
    }
    
    # Получаем информацию о файле для получения ссылки на скачивание
    response = requests.get(f'https://cloud-api.yandex.net/v1/disk/resources/download?path={file_path}', headers=headers)
    
    if response.status_code == 200:
        download_info = response.json()
        return download_info['href']  # Ссылка для скачивания файла
    else:
        logger.error(f'Ошибка при получении ссылки на файл: {response.status_code} - {response.text}')
        return None

def download_image(file_path):
    file_url = get_file_url(file_path)  # Получаем прямую ссылку на файл
    
    if file_url:
        response = requests.get(file_url)
        if response.status_code == 200:
            return Image.open(BytesIO(response.content))
        else:
            logger.error("Ошибка при загрузке изображения: %s", response.status_code)
            return None
    else:
        logger.error("Не удалось получить ссылку на файл.")
        return None

def extract_text_from_image(image):
    return pytesseract.image_to_string(image)

def search_photos_in_folders(query):
    logger.info("Поиск фотографий по запросу: %s", query)
    all_items = get_all_files()  # Получаем корневые файлы и папки
    photos = []

    for item in all_items:
        if item['type'] == 'dir':
            # Если это папка, получаем содержимое этой папки
            sub_items = get_all_files(item['path'])
            for sub_item in sub_items:
                if (sub_item['type'] == 'file' and sub_item['name'].lower().endswith(('.png', '.jpg', '.jpeg')) and 
                    query.lower() in sub_item['name'].lower()):
                    photos.append(sub_item['path'])  # Добавляем путь к фото
        elif item['type'] == 'file' and item['name'].lower().endswith(('.png', '.jpg', '.jpeg')) and query.lower() in item['name'].lower():
            photos.append(item['path'])  # Добавляем путь к фото

    logger.info("Найдено %d фотографий по запросу: %s", len(photos), query)

    # Теперь выполняем OCR на найденных фотографиях
    ocr_results = []
    
    for photo in photos:
        image = download_image(photo)

        if image is not None:
            text = extract_text_from_image(image)
            if query.lower() in text.lower():
                ocr_results.append(photo)  # Добавляем путь к фото, если текст найден

    logger.info("Найдено %d фотографий по тексту после OCR.", len(ocr_results))
    
    return ocr_results or photos  # Возвращаем результаты OCR или оригинальные фотографии

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("Получена команда /start от %s", update.effective_user.first_name)
    await update.message.reply_text('Привет! Напиши мне запрос для поиска фотографий на Яндекс.Диске.')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.message.text
    logger.info("Получено сообщение от %s: %s", update.effective_user.first_name, query)
    
    photos = search_photos_in_folders(query)

    if photos:
        for photo in photos:
            await update.message.reply_text(photo + '\n')  # Отправляем ссылку на фото
    else:
        await update.message.reply_text('Ничего не найдено.')
        logger.info("По запросу '%s' ничего не найдено.", query)

def main():
    logger.info("Запуск бота...")
    
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling()
    
if __name__ == '__main__':
    main()