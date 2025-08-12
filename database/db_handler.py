import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'database', 'database.db')

def init_db():

    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    print("Проверка структуры базы данных...")
    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            language_code TEXT DEFAULT 'ru',
            xp INTEGER DEFAULT 0
        )
    """)
    # Seen modules table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS seen_modules (
            user_id INTEGER,
            module_id INTEGER,
            seen_date DATE,
            PRIMARY KEY (user_id, module_id),
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    """)

    # Solved debunks table
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS solved_debunks (
                user_id INTEGER,
                case_id TEXT,
                solved_date DATE,
                PRIMARY KEY (user_id, case_id),
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
    print("Структура базы данных в порядке.")
    conn.commit()
    conn.close()

def get_or_create_user(user_id: int, username: str = None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    if not user:
        cursor.execute("INSERT INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
        conn.commit()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
    conn.close()
    return {'user_id': user[0], 'username': user[1], 'language_code': user[2], 'xp': user[3]}

def set_user_language(user_id: int, lang_code: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET language_code = ? WHERE user_id = ?", (lang_code, user_id))
    conn.commit()
    conn.close()

def get_user_xp(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT xp FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

def change_xp(user_id: int, amount: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET xp = xp + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def mark_module_as_seen(user_id: int, module_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    today = datetime.now().date()
    cursor.execute("INSERT OR REPLACE INTO seen_modules (user_id, module_id, seen_date) VALUES (?, ?, ?)",
                   (user_id, module_id, today))
    conn.commit()
    conn.close()

def get_seen_modules_for_quiz(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Логика для еженедельного квиза: берем модули за последние 7 дней
    cursor.execute("""
        SELECT DISTINCT module_id FROM seen_modules
        WHERE user_id = ? AND seen_date >= date('now', '-7 days')
    """, (user_id,))
    modules = cursor.fetchall()
    conn.close()
    return [m[0] for m in modules]

def get_all_users():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, language_code FROM users")
    users = cursor.fetchall()
    conn.close()
    return users

def mark_debunk_as_solved(user_id: int, case_id: str):
    """Отмечает кейс как решенный пользователем."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    today = datetime.now().date()
    cursor.execute("INSERT OR IGNORE INTO solved_debunks (user_id, case_id, solved_date) VALUES (?, ?, ?)",
                   (user_id, case_id, today))
    conn.commit()
    conn.close()

def get_solved_debunk_ids(user_id: int) -> list[str]:
    """Возвращает список ID кейсов, решенных пользователем."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT case_id FROM solved_debunks WHERE user_id = ?", (user_id,))
    cases = cursor.fetchall()
    conn.close()
    return [c[0] for c in cases]