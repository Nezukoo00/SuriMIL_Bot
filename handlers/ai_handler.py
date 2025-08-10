import google.generativeai as genai
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, filters
from config import GEMINI_API_KEY
from database import db_handler
from .utils import get_text

# Определяем состояние диалога
AWAITING_QUESTION, = range(1)

# Настройка Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')


async def start_ai_dialog(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начинает диалог с ИИ, отправляя приветственное сообщение."""
    user_id = update.effective_user.id
    user = db_handler.get_or_create_user(user_id)
    lang = user['language_code']

    # Отправляем приветствие и просьбу задать вопрос
    await update.message.reply_text(get_text('ai_welcome_prompt', lang))

    # Переходим в состояние ожидания вопроса
    return AWAITING_QUESTION


async def handle_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает полученный от пользователя вопрос и отвечает на него."""
    user_id = update.effective_user.id
    user = db_handler.get_or_create_user(user_id)
    lang = user['language_code']
    question = update.message.text

    # Отправляем "думающее" сообщение
    thinking_message = await update.message.reply_text(get_text('ask_ai_thinking', lang))

    try:
        # Промпт для Gemini
        prompt = f"""Ты — SuriMIL, дружелюбный и умный эксперт по медиаграмотности. 
        Ответь на вопрос пользователя кратко, ясно и по делу. 
        Не используй форматирование markdown. Ответ дай на языке: {lang}.
        Вопрос пользователя: "{question}"
        """
        response = await model.generate_content_async(prompt)
        await thinking_message.edit_text(response.text)
    except Exception as e:
        print(f"Ошибка Gemini API: {e}")
        await thinking_message.edit_text("Произошла ошибка при обращении к ИИ. Попробуй позже.")

    # Завершаем диалог
    return ConversationHandler.END


async def cancel_dialog(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отменяет текущий диалог с ИИ."""
    user = db_handler.get_or_create_user(update.effective_user.id)
    lang = user['language_code']
    await update.message.reply_text(get_text('quiz_cancelled', lang)) # Можно использовать текст отмены квиза или добавить новый
    return ConversationHandler.END