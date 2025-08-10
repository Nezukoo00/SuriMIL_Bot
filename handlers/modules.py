import json
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes, JobQueue
from database import db_handler
from .utils import get_text

# Загружаем модули
with open('content/modules_ru.json', 'r', encoding='utf-8') as f:
    modules_ru = json.load(f)
with open('content/modules_en.json', 'r', encoding='utf-8') as f:
    modules_en = json.load(f)


def get_today_module(lang: str):
    """Выбирает модуль дня по номеру дня недели (0=Пн, 6=Вс)"""
    day_of_week = datetime.now().weekday()
    modules = modules_ru if lang == 'ru' else modules_en
    return modules[day_of_week]


async def send_module_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db_handler.get_or_create_user(user_id)
    lang = user['language_code']

    module = get_today_module(lang)
    intro_text = get_text('module_intro', lang)

    await update.message.reply_html(f"{intro_text}<b>{module['title']}</b>\n\n{module['text']}")
    db_handler.mark_module_as_seen(user_id, module['id'])


async def broadcast_module(context: ContextTypes.DEFAULT_TYPE):
    """Рассылает ежедневный модуль всем пользователям"""
    users = db_handler.get_all_users()
    for user_id, lang in users:
        try:
            module = get_today_module(lang)
            intro_text = get_text('module_intro', lang)
            await context.bot.send_message(
                chat_id=user_id,
                text=f"{intro_text}<b>{module['title']}</b>\n\n{module['text']}",
                parse_mode='HTML'
            )
            db_handler.mark_module_as_seen(user_id, module['id'])
        except Exception as e:
            print(f"Не удалось отправить сообщение пользователю {user_id}: {e}")