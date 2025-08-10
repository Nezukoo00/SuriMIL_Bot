import os
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

# Получаем токен. Если его нет, выйдет ошибка.
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("Не найден TELEGRAM_TOKEN в .env файле!")

# Ключ Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("Не найден GEMINI_API_KEY в .env файле!")

# Путь к базе данных
DB_PATH = os.path.join("database", "database.db")