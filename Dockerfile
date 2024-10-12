# Используем базовый образ Python
FROM python:3.9-slim

# Указываем рабочую директорию внутри контейнера
WORKDIR /app

# Копируем все файлы проекта в контейнер
COPY . /app

# Устанавливаем зависимости (если есть файл requirements.txt)
RUN pip install --no-cache-dir -r requirements.txt

# Запускаем ваше приложение
CMD ["flask", "run", "--host=0.0.0.0"]
