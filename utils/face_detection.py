import cv2
import logging
from pathlib import Path
import tempfile
from aiogram.types import PhotoSize
import aiohttp
import os

logger = logging.getLogger(__name__)

# Путь к XML файлу классификатора (изменим на более надежный путь)
CASCADE_PATH = Path(__file__).parent.parent / "data" / "haarcascade_frontalface_default.xml"

# Создаем директорию, если её нет
CASCADE_PATH.parent.mkdir(parents=True, exist_ok=True)

async def download_cascade_if_not_exists():
    """Скачивает XML файл классификатора, если его нет"""
    if not CASCADE_PATH.exists():
        url = "https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                content = await response.text()
                CASCADE_PATH.write_text(content)
                logger.info("Классификатор для распознавания лиц успешно загружен")

async def has_face_in_photo(photo: PhotoSize) -> bool:
    """Проверяет наличие лица на фотографии"""
    try:
        # Скачиваем классификатор, если его нет
        await download_cascade_if_not_exists()
        
        # Создаем временный файл для сохранения фото
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            # Скачиваем фото
            file = await photo.download(destination_file=temp_file.name)
            
            # Загружаем классификатор
            face_cascade = cv2.CascadeClassifier(str(CASCADE_PATH))
            
            # Читаем изображение
            img = cv2.imread(temp_file.name)
            if img is None:
                logger.error("Не удалось прочитать изображение")
                return False
                
            # Конвертируем в градации серого
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Ищем лица
            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )
            
            # Удаляем временный файл
            os.unlink(temp_file.name)
            
            # Возвращаем True, если найдено хотя бы одно лицо
            return len(faces) > 0
            
    except Exception as e:
        logger.error(f"Ошибка при проверке лица на фото: {e}")
        return False 