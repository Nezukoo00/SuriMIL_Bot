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


    # --- НАЧАЛО ОТЛАДКИ ---
    print("\n--- Попытка покупки стикера ---")
    print(f"Получены данные с кнопки: {query.data}")

    user_id = query.from_user.id
    user = db_handler.get_or_create_user(user_id)
    lang = user['language_code']

    sticker_id = query.data.removeprefix('buy_sticker_')
    print(f"Извлечен ID стикера: '{sticker_id}'")

    # Находим стикер в наших данных
    sticker_to_buy = next((s for s in stickers_data if s['id'] == sticker_id), None)

    # Очень важная проверка
    print(f"Результат поиска стикера в данных: {sticker_to_buy}")

    if not sticker_to_buy:
        # Если стикер не найден, мы увидим это сообщение в консоли
        print("!!! ОШИБКА: Стикер с таким ID не найден в stickers.json. Функция завершается.")
        return

    print("Стикер найден. Проверяем баланс XP.")
    # --- КОНЕЦ ОТЛАДКИ ---

    user_xp = user['xp']
    price = sticker_to_buy['price']

    if user_xp >= price:
        db_handler.change_xp(user_id, -price)
        new_xp = user_xp - price
        sticker_path = sticker_to_buy['file_path']
        try:
            with open(sticker_path, 'rb') as sticker_file:
                await context.bot.send_sticker(chat_id=user_id, sticker=sticker_file)
            success_text = get_text('store_buy_success', lang, new_xp=new_xp)
            await query.edit_message_text(success_text)
        except FileNotFoundError:
            print(f"!!! ФАТАЛЬНАЯ ОШИБКА: Файл стикера не найден по пути: {sticker_path}")
            await context.bot.send_message(chat_id=user_id,
                                           text="Ой, кажется, этот стикер временно недоступен. Попробуйте позже.")
            db_handler.change_xp(user_id, price)
    else:
        needed_xp = price - user_xp
        fail_text = get_text('store_buy_fail', lang, needed=needed_xp)
        await context.bot.answer_callback_query(callback_query_id=query.id, text=fail_text, show_alert=True)