from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from database import db_handler
from .utils import get_text


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    db_handler.get_or_create_user(user.id, user.username)
    keyboard = [
        [InlineKeyboardButton("Русский 🇷🇺", callback_data='set_lang_ru')],
        [InlineKeyboardButton("English 🇬🇧", callback_data='set_lang_en')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_html(
        get_text('welcome', 'ru', user_mention=user.mention_html()),
        reply_markup=reply_markup
    )


async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    lang_code = query.data.split('_')[-1]
    db_handler.set_user_language(query.from_user.id, lang_code)

    await query.edit_message_text(text=get_text('lang_chosen_prefix', lang_code))
    await show_main_menu(update.effective_chat.id, lang_code, context)


async def show_main_menu(chat_id: int, lang: str, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [get_text('main_menu_module', lang)],
        [get_text('main_menu_quiz', lang), get_text('main_menu_store', lang)],
        [get_text('main_menu_ask', lang)]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await context.bot.send_message(
        chat_id=chat_id,
        text=get_text('main_menu', lang),
        reply_markup=reply_markup
    )