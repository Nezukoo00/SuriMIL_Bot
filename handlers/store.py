import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import db_handler
from .utils import get_text

# Загружаем стикеры
with open('assets/stickers.json', 'r', encoding='utf-8') as f:
    stickers_data = json.load(f)


async def store_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db_handler.get_or_create_user(user_id)
    lang = user['language_code']
    xp = user['xp']

    intro_text = get_text('store_intro', lang, xp=xp)

    keyboard = []
    for sticker in stickers_data:
        # Получаем имя стикера на нужном языке
        sticker_name_in_lang = sticker['name'].get(lang, sticker['name']['en'])
        button_text = get_text('store_item', lang, name=sticker_name_in_lang, price=sticker['price'])
        keyboard.append([
            InlineKeyboardButton(button_text, callback_data=f"buy_sticker_{sticker['id']}")
        ])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(intro_text, reply_markup=reply_markup)


async def handle_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    user = db_handler.get_or_create_user(user_id)
    lang = user['language_code']

    sticker_id = query.data.split('_')[-1]

    # Находим стикер в наших данных
    sticker_to_buy = next((s for s in stickers_data if s['id'] == sticker_id), None)

    if not sticker_to_buy:
        return

    user_xp = user['xp']
    price = sticker_to_buy['price']

    if user_xp >= price:
        # Списываем XP
        db_handler.change_xp(user_id, -price)
        new_xp = user_xp - price

        # Отправляем стикер
        await context.bot.send_sticker(chat_id=user_id, sticker=sticker_to_buy['file_id'])

        # Сообщаем об успехе
        success_text = get_text('store_buy_success', lang, new_xp=new_xp)
        await query.edit_message_text(success_text)
    else:
        # Недостаточно средств
        needed_xp = price - user_xp
        fail_text = get_text('store_buy_fail', lang, needed_xp=needed_xp)
        # Отправляем всплывающее уведомление
        await context.bot.answer_callback_query(callback_query_id=query.id, text=fail_text, show_alert=True)