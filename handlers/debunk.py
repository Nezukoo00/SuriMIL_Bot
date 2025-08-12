import json
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from database import db_handler
from .utils import get_text

# Загружаем дела для разбора
with open('content/debunks_ru.json', 'r', encoding='utf-8') as f:
    debunks_ru = json.load(f)
with open('content/debunks_en.json', 'r', encoding='utf-8') as f:
    debunks_en = json.load(f)

# Состояния диалога
AWAITING_ANSWER, = range(1)
DEBUNK_XP_REWARD = 25

# --- Helper Functions ---

def get_random_case(lang: str, user_id: int):
    """Выбирает случайный нерешенный кейс для пользователя."""
    all_cases = debunks_ru if lang == 'ru' else debunks_en
    solved_case_ids = db_handler.get_solved_debunk_ids(user_id)

    unsolved_cases = [
        case for case in all_cases if case['id'] not in solved_case_ids
    ]

    return random.choice(unsolved_cases) if unsolved_cases else None


async def send_step_question(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет вопрос текущего шага с кнопками, включая кнопку 'Отмена'."""
    case = context.user_data['debunk_case']
    step_index = context.user_data['debunk_step']
    step_data = case['steps'][step_index]

    keyboard = [
        [InlineKeyboardButton(text, callback_data=f"debunk_{key}")]
        for key, text in step_data['options'].items()
    ]

    keyboard.append([InlineKeyboardButton("❌ Отмена (Cancel)", callback_data="debunk_cancel")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(
        chat_id=chat_id,
        text=step_data['question'],
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def end_debunk_session(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Завершает сессию, начисляет XP, отмечает кейс как решенный."""
    case = context.user_data['debunk_case']
    user_id = chat_id
    lang = db_handler.get_or_create_user(user_id)['language_code']

    xp_to_award = case.get('xp_reward', DEBUNK_XP_REWARD)
    db_handler.change_xp(user_id, xp_to_award)

    #  Отмечаем кейс как решенный
    db_handler.mark_debunk_as_solved(user_id, case['id'])

    await context.bot.send_message(chat_id=user_id, text=case['final_message'], parse_mode='Markdown')
    await context.bot.send_message(chat_id=user_id, text=get_text('debunk_xp_award', lang, xp=xp_to_award))

    context.user_data.pop('debunk_case', None)
    context.user_data.pop('debunk_step', None)
    return ConversationHandler.END

# --- Main Conversation Handlers ---

async def start_debunk(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начинает механику разбора фейка."""
    user_id = update.effective_user.id
    lang = db_handler.get_or_create_user(user_id)['language_code']

    case = get_random_case(lang, user_id)
    if not case:
        await update.message.reply_text(get_text('debunk_no_cases', lang))
        return ConversationHandler.END

    context.user_data['debunk_case'] = case
    context.user_data['debunk_step'] = 0

    if case.get('initial_photo'):
        await update.message.reply_photo(
            photo=case['initial_photo'],
            caption=case['initial_message'],
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(case['initial_message'], parse_mode='Markdown')

    await send_step_question(update.effective_chat.id, context)
    return AWAITING_ANSWER


async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает ответ пользователя и решает, что делать дальше."""
    query = update.callback_query
    await query.answer()

    case = context.user_data['debunk_case']
    step_index = context.user_data['debunk_step']
    step_data = case['steps'][step_index]
    selected_option = query.data.removeprefix('debunk_')

    # Сначала удаляем предыдущее сообщение с вопросом, чтобы не было дублей
    await query.delete_message()

    if selected_option == step_data['correct_option']:
        # --- ПОЛЬЗОВАТЕЛЬ ОТВЕТИЛ ПРАВИЛЬНО ---
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"*{step_data['options'][selected_option]}*\n\n_{step_data['feedback_correct']}_",
            parse_mode='Markdown'
        )
        context.user_data['debunk_step'] += 1

        if context.user_data['debunk_step'] < len(case['steps']):
            # Есть еще шаги, отправляем следующий
            await send_step_question(query.message.chat_id, context)
            return AWAITING_ANSWER
        else:
            # Шаги закончились, завершаем сессию
            return await end_debunk_session(query.message.chat_id, context)
    else:
        # --- ПОЛЬЗОВАТЕЛЬ ОТВЕТИЛ НЕПРАВИЛЬНО ---
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"*{step_data['options'][selected_option]}*\n\n_{step_data['hint_incorrect']}_",
            parse_mode='Markdown'
        )
        # Отправляем тот же вопрос еще раз
        await send_step_question(query.message.chat_id, context)
        return AWAITING_ANSWER


async def cancel_debunk(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отменяет расследование (реагирует и на команду /cancel, и на кнопку)."""
    query = update.callback_query
    user_id = update.effective_user.id
    lang = db_handler.get_or_create_user(user_id)['language_code']

    if query:
        # Если это нажатие кнопки, удаляем сообщение с вопросом
        await query.delete_message()

    # Очищаем данные
    context.user_data.pop('debunk_case', None)
    context.user_data.pop('debunk_step', None)

    await context.bot.send_message(chat_id=user_id, text=get_text('debunk_cancelled', lang))
    return ConversationHandler.END