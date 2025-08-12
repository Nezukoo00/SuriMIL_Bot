import logging
import datetime
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ConversationHandler,
)

from config import TELEGRAM_TOKEN
from database import db_handler
from handlers import common, modules, store, quiz, ai_handler, debunk
from handlers.utils import get_text


# Включаем логирование
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Определяем фильтры для кнопок главного меню на разных языках
module_button_filter = filters.TEXT & (
        filters.Regex(f"^{get_text('main_menu_module', 'ru')}$") |
        filters.Regex(f"^{get_text('main_menu_module', 'en')}$")
)
store_button_filter = filters.TEXT & (
        filters.Regex(f"^{get_text('main_menu_store', 'ru')}$") |
        filters.Regex(f"^{get_text('main_menu_store', 'en')}$")
)
quiz_button_filter = filters.TEXT & (
        filters.Regex(f"^{get_text('main_menu_quiz', 'ru')}$") |
        filters.Regex(f"^{get_text('main_menu_quiz', 'en')}$")
)
ask_button_filter = filters.TEXT & (
        filters.Regex(f"^{get_text('main_menu_ask', 'ru')}$") |
        filters.Regex(f"^{get_text('main_menu_ask', 'en')}$")
)
debunk_button_filter = filters.TEXT & (
        filters.Regex(f"^{get_text('main_menu_debunk', 'ru')}$") |
        filters.Regex(f"^{get_text('main_menu_debunk', 'en')}$")
)
main_menu_buttons_filter = (
    module_button_filter | store_button_filter | quiz_button_filter |
    debunk_button_filter | ask_button_filter
)


def main() -> None:
    """Основная функция запуска бота."""
    # Инициализация БД при старте
    db_handler.init_db()

    # Создание Application
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # --- Обработчик диалога для квиза ---
    quiz_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(quiz_button_filter, quiz.quiz_command)],
        states={
            quiz.ANSWERING: [CallbackQueryHandler(quiz.handle_answer, pattern='^ans_')],
        },
        fallbacks=[CommandHandler('cancel', quiz.cancel_quiz)],
    )

    # ---ОБРАБОТЧИК ДИАЛОГА ДЛЯ ИИ ---
    ai_conv_handler = ConversationHandler(
        entry_points=[
            # Точка входа №1: Нажатие на кнопку с точным текстом.
            MessageHandler(ask_button_filter, ai_handler.start_ai_dialog),
            # Точка входа №2: Явная команда /ask.
            CommandHandler("ask", ai_handler.start_ai_dialog)
        ],
        states={
            # Состояние, в котором бот ждет вопрос от пользователя.
            # Когда ИИ ждет вопрос, он будет реагировать на любой текст,
            # который НЕ является командой И НЕ является кнопкой главного меню.
            ai_handler.AWAITING_QUESTION: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND & ~main_menu_buttons_filter,
                    ai_handler.handle_question
                )
            ]
        },
        fallbacks=[CommandHandler('cancel', ai_handler.cancel_dialog)

                   ]

    )

    # --- ОБРАБОТЧИК ДЛЯ РАЗБОРА ФЕЙКОВ ---
    debunk_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("debunk", debunk.start_debunk),
            MessageHandler(debunk_button_filter, debunk.start_debunk)
        ],
        states={
            debunk.AWAITING_ANSWER: [

                CallbackQueryHandler(debunk.cancel_debunk, pattern='^debunk_cancel$'),
                CallbackQueryHandler(debunk.handle_answer, pattern='^debunk_')
            ],
        },
        fallbacks=[CommandHandler('cancel', debunk.cancel_debunk)],
    )

    # --- Регистрация всех обработчиков ---
    application.add_handler(CommandHandler("start", common.start))
    application.add_handler(CallbackQueryHandler(common.set_language, pattern='^set_lang_'))

    # Обработчики для кнопок главного меню
    application.add_handler(MessageHandler(module_button_filter, modules.send_module_command))
    application.add_handler(MessageHandler(store_button_filter, store.store_command))


    # Команды для прямого доступа
    application.add_handler(CommandHandler("module", modules.send_module_command))
    application.add_handler(CommandHandler("store", store.store_command))
    application.add_handler(CommandHandler("quiz", quiz.quiz_command))


    # Добавляем обработчик квиза
    application.add_handler(quiz_conv_handler)
    application.add_handler(ai_conv_handler)
    application.add_handler(debunk_conv_handler)

    # Обработчик для кнопок магазина
    application.add_handler(CallbackQueryHandler(store.handle_purchase, pattern='^buy_sticker_'))

    # --- Настройка ежедневной рассылки ---
    job_queue = application.job_queue
    # Время в UTC. 9:00 МСК = 6:00 UTC.Часовой пояс.
    daily_time = datetime.time(hour=7, minute=0, tzinfo=datetime.timezone.utc)
    job_queue.run_daily(modules.broadcast_module, time=daily_time)

    # Запуск бота
    logger.info("Бот запускается...")
    application.run_polling()


if __name__ == "__main__":
    main()