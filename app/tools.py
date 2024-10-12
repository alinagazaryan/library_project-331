import hashlib
import uuid
import os
from werkzeug.utils import secure_filename
from models import Image  # Предполагается, что модель Image определена в файле models.py
from app import db  # Предполагается, что db это объект SQLAlchemy
from flask import request

class ImageSaver:
    def __init__(self, file):
        self.file = file

    def save(self):
        # Проверяем, существует ли изображение с таким же MD5 хэшем
        self.img = self.__find_by_md5_hash()
        if self.img is not None:
            return self.img  # Возвращаем существующее изображение, если найдено
        
        # Если совпадений не найдено, генерируем уникальный ID и обрабатываем файл
        _, file_extension = os.path.splitext(self.file.filename)
        uniq_id_name = str(uuid.uuid4())
        
        # Создаем новый объект Image с уникальными атрибутами
        self.img = Image(
            id=uniq_id_name,
            file_name=uniq_id_name + file_extension,
            mime_type=self.file.mimetype,
            md5_hash=self.md5_hash)  # md5_hash устанавливается методом __find_by_md5_hash()
        
        # Сохраняем файл на диск
        self.file.save(
            os.path.join(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media', 'images'),
                         self.img.file_name))
        
        # Добавляем объект Image в сессию базы данных и коммитим изменения
        db.session.add(self.img)
        db.session.commit()
        
        return self.img  # Возвращаем сохраненный объект Image

    def __find_by_md5_hash(self):
        # Вычисляем MD5 хэш содержимого файла
        self.md5_hash = hashlib.md5(self.file.read()).hexdigest()
        self.file.seek(0)  # Сбрасываем указатель файла в начало
        
        # Запрашиваем из базы данных объект Image с соответствующим MD5 хэшем
        return Image.query.filter(Image.md5_hash == self.md5_hash).first()

# Функция для извлечения параметров из формы запроса на основе заданного словаря
def extract_params(dict):
    return {p: request.form.get(p) for p in dict}
