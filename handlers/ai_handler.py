import google.generativeai as genai
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, filters
from config import GEMINI_API_KEY
from database import db_handler
from .utils import get_text

# Определяем состояние диалога
AWAITING_QUESTION, = range(1)

SYSTEM_PROMPT = """Ты — SuriMIL, дружелюбный и умный эксперт по медиаграмотности.
Твоя единственная задача — отвечать на вопросы, связанные с медиаграмотностью, фейками, фактчекингом, пропагандой и цифровой гигиеной.
Если пользователь задает вопрос не по теме (например, о погоде, просит написать стих, спрашивает личные вещи), ты должен вежливо отказаться и напомнить о своей специализации.
Отвечай кратко, ясно и по делу. Всегда отвечай на том языке, на котором задан последний вопрос пользователя.Если пользователь спрашивает "Эта новость — фейк?", твой ответ должен быть таким:
1. Не отвечай "да" или "нет".
2. Задай встречный вопрос: "Интересный вопрос. Давай разберемся вместе. Что тебя смущает в этой новости?" или "С чего бы ты начал проверку?".
3. Спроси об источнике, эмоциональной окраске, наличии доказательств.
4. Предложи воспользоваться инструментами: "Как насчет того, чтобы сделать обратный поиск по картинке из статьи?".
5. Давай прямой ответ только если пользователь несколько раз попросит об этом прямо ("скажи прямо, да или нет")."""

# Настройка Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(
    model_name='gemini-1.5-flash',
    system_instruction=SYSTEM_PROMPT)


async def start_ai_dialog(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начинает диалог с ИИ, создавая сессию чата."""
    user_id = update.effective_user.id
    user = db_handler.get_or_create_user(user_id)
    lang = user['language_code']

    # Создаем новую сессию чата с историей и сохраняем ее для пользователя
    # Это позволит ИИ "помнить" предыдущие сообщения в рамках одного диалога
    context.user_data['ai_chat_session'] = model.start_chat(history=[])

    await update.message.reply_text(get_text('ai_welcome_prompt', lang))

    # Переходим в состояние ожидания вопроса
    return AWAITING_QUESTION


async def handle_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает вопрос пользователя в рамках текущей сессии чата."""
    user_id = update.effective_user.id
    user = db_handler.get_or_create_user(user_id)
    lang = user['language_code']
    question = update.message.text

    # Получаем текущую сессию чата из user_data
    chat_session = context.user_data.get('ai_chat_session')
    if not chat_session:
        # Если сессия потеряна, начинаем заново
        return await start_ai_dialog(update, context)

    thinking_message = await update.message.reply_text(get_text('ask_ai_thinking', lang))

    try:
        # Отправляем сообщение в текущий чат, Gemini сам учтет историю
        # Мы больше не передаем весь промпт каждый раз
        response = await chat_session.send_message_async(question)
        await thinking_message.edit_text(response.text)
    except Exception as e:
        print(f"Ошибка Gemini API: {e}")
        await thinking_message.edit_text("Произошла ошибка при обращении к ИИ. Попробуй позже.")


    # Возвращаемся в то же состояние, чтобы ждать следующий вопрос
    return AWAITING_QUESTION


async def cancel_dialog(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отменяет текущий диалог с ИИ и очищает память."""
    user = db_handler.get_or_create_user(update.effective_user.id)
    lang = user['language_code']

    # Очищаем данные сессии из памяти
    if 'ai_chat_session' in context.user_data:
        del context.user_data['ai_chat_session']

    await context.bot.send_message(
        chat_id=update.effective_user.id,
        text=get_text('ai_cancel_dialog', lang)
    )

    return ConversationHandler.END