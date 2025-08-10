import json
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from database import db_handler
from .utils import get_text

# Загружаем квизы
with open('content/quizzes_ru.json', 'r', encoding='utf-8') as f:
    quizzes_ru = json.load(f)
with open('content/quizzes_en.json', 'r', encoding='utf-8') as f:
    quizzes_en = json.load(f)

# Состояния для диалога
ANSWERING, = range(1)
XP_PER_CORRECT_ANSWER = 10


async def quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начинает квиз."""
    user_id = update.effective_user.id
    user = db_handler.get_or_create_user(user_id)
    lang = user['language_code']

    # Получаем ID модулей, которые пользователь видел за последнюю неделю
    seen_module_ids = db_handler.get_seen_modules_for_quiz(user_id)

    if not seen_module_ids:
        await update.message.reply_text(get_text('quiz_no_modules', lang))
        return ConversationHandler.END

    all_questions = quizzes_ru if lang == 'ru' else quizzes_en

    # Отбираем вопросы по виденным модулям
    user_questions = [q for q in all_questions if q['module_id'] in seen_module_ids]

    if not user_questions:
        await update.message.reply_text(get_text('quiz_no_modules', lang))
        return ConversationHandler.END

    random.shuffle(user_questions)

    # Сохраняем данные квиза для пользователя
    context.user_data['quiz_questions'] = user_questions
    context.user_data['current_q_index'] = 0
    context.user_data['score'] = 0

    await update.message.reply_text(get_text('quiz_intro', lang))
    await send_question(update.effective_chat.id, context)

    return ANSWERING


async def send_question(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет текущий вопрос."""
    user_data = context.user_data
    q_index = user_data['current_q_index']
    questions = user_data['quiz_questions']
    question_data = questions[q_index]

    user = db_handler.get_or_create_user(chat_id)
    lang = user['language_code']

    title = get_text('quiz_question_title', lang, current=q_index + 1, total=len(questions))

    keyboard = []
    for i, option in enumerate(question_data['options']):
        keyboard.append([InlineKeyboardButton(option, callback_data=f"ans_{i}")])

    await context.bot.send_message(
        chat_id=chat_id,
        text=f"{title}\n\n<b>{question_data['question']}</b>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает ответ пользователя."""
    query = update.callback_query
    await query.answer()

    user_data = context.user_data
    q_index = user_data['current_q_index']
    questions = user_data['quiz_questions']
    question_data = questions[q_index]

    user_id = query.from_user.id
    user = db_handler.get_or_create_user(user_id)
    lang = user['language_code']

    selected_option_index = int(query.data.split('_')[1])
    correct_option_index = question_data['correct']

    result_text = ""
    if selected_option_index == correct_option_index:
        user_data['score'] += 1
        result_text = get_text('quiz_correct', lang)
    else:
        correct_answer_text = question_data['options'][correct_option_index]
        result_text = get_text('quiz_incorrect', lang, correct_answer=correct_answer_text)

    # Редактируем сообщение с вопросом, чтобы показать результат и убрать кнопки
    await query.edit_message_text(
        text=f"<b>{question_data['question']}</b>\n\n<i>Ваш ответ: {question_data['options'][selected_option_index]}</i>\n\n{result_text}",
        parse_mode='HTML'
    )

    user_data['current_q_index'] += 1

    if user_data['current_q_index'] < len(questions):
        await send_question(query.message.chat_id, context)
        return ANSWERING
    else:
        # Квиз окончен
        score = user_data['score']
        total = len(questions)
        xp_earned = score * XP_PER_CORRECT_ANSWER

        db_handler.change_xp(user_id, xp_earned)

        results_title = get_text('quiz_results_title', lang)
        results_score = get_text('quiz_results_score', lang, score=score, total=total)
        results_xp = get_text('quiz_results_xp', lang, xp=xp_earned)

        await context.bot.send_message(
            chat_id=user_id,
            text=f"{results_title}\n{results_score}\n{results_xp}"
        )
        # Очищаем данные квиза
        user_data.clear()
        return ConversationHandler.END


async def cancel_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отменяет квиз."""
    context.user_data.clear()
    await update.message.reply_text("Квиз отменен.")
    return ConversationHandler.END