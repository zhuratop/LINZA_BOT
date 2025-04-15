import asyncio
import logging
import sqlite3
import sys

from typing import Optional
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
    CallbackQueryHandler
)

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
MENU, FILL_FORM, PARTNERSHIP = range(3)

# Подключение к базе данных
conn = sqlite3.connect('bot_data.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS answers
                  (id INTEGER PRIMARY KEY AUTOINCREMENT,
                   q1 TEXT, q2 TEXT, q3 TEXT, q4 TEXT, q5 TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS users
                  (user_id INTEGER PRIMARY KEY)''')
conn.commit()


# ================== ОСНОВНЫЕ ОБРАБОТЧИКИ ================== #
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик команды /start"""
    keyboard = [
        ['📝 Заполнить анкету'],
        ['🤝 Партнерство'],
        ['🆘 Поддержка'],
        ['🔄 Перезапустить бота']
    ]
    await update.message.reply_text(
        "Добро пожаловать! Выберите опцию:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return MENU


async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик главного меню"""
    text = update.message.text
    user_id = update.effective_user.id

    if text == '📝 Заполнить анкету':
        cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
        if cursor.fetchone():
            await update.message.reply_text("❗ Вы уже заполняли анкету.")
            return MENU

        context.user_data.clear()
        context.user_data['question_number'] = 1
        await update.message.reply_text(
            "Вопрос 1: Как вас зовут?",
            reply_markup=ReplyKeyboardRemove()
        )
        return FILL_FORM

    elif text == '🤝 Партнерство':
        keyboard = [
            ['🔗 Реферальная программа'],
            ['👥 Для рекрутеров'],
            ['🚀 BizDev'],
            ['🔙 Назад']
        ]
        await update.message.reply_text(
            "Выберите тип партнерства:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return PARTNERSHIP

    elif text == '🆘 Поддержка':
        keyboard = [[InlineKeyboardButton("📨 Написать менеджеру", url="t.me/zhuratop_trep")]]
        await update.message.reply_text(
            "Свяжитесь с нашим менеджером:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return MENU

    elif text == '🔄 Перезапустить бота':
        return await start(update, context)


# ================== ЗАПОЛНЕНИЕ АНКЕТЫ ================== #
async def handle_answers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик ответов анкеты"""
    text = update.message.text
    q_num = context.user_data.get('question_number', 1)

    # Кнопки навигации
    nav_keyboard = ReplyKeyboardMarkup(
        [['🔙 Назад', '🏠 Меню']],
        resize_keyboard=True
    )

    # Обработка кнопки Меню
    if text == '🏠 Меню':
        await update.message.reply_text(
            "Вы вернулись в главное меню.",
            reply_markup=ReplyKeyboardRemove()
        )
        return await start(update, context)

    # Обработка кнопки Назад
    if text == '🔙 Назад':
        if q_num > 1:
            q_num -= 1
            context.user_data['question_number'] = q_num
            await update.message.reply_text(
                f"Вопрос {q_num}: Повторно введите ответ.",
                reply_markup=nav_keyboard
            )
            return FILL_FORM
        else:
            await update.message.reply_text("Вы на первом вопросе.")
            return FILL_FORM

    # Сохраняем ответ
    context.user_data[f'q{q_num}'] = text
    q_num += 1

    if q_num > 5:
        # Сохраняем ответы в БД
        cursor.execute('''INSERT INTO answers 
                       (q1, q2, q3, q4, q5) 
                       VALUES (?, ?, ?, ?, ?)''',
                       (context.user_data.get('q1'),
                        context.user_data.get('q2'),
                        context.user_data.get('q3'),
                        context.user_data.get('q4'),
                        context.user_data.get('q5')))
        # Сохраняем user_id
        cursor.execute("INSERT INTO users (user_id) VALUES (?)", (update.effective_user.id,))
        conn.commit()

        await update.message.reply_text("✅ Анкета сохранена!")
        return await start(update, context)

    context.user_data['question_number'] = q_num
    await update.message.reply_text(
        f"Вопрос {q_num}: Ваш опыт работы?",
        reply_markup=nav_keyboard
    )
    return FILL_FORM

# ================== ПАРТНЕРСТВО ================== #
async def handle_partnership(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик раздела партнерства"""
    text = update.message.text
    response = {
        '🔗 Реферальная программа': 'Реферальная программа: ...',
        '👥 Для рекрутеров': 'Информация для рекрутеров: ...',
        '🚀 BizDev': 'BizDev сотрудничество: ...',
        '🔙 Назад': None
    }.get(text)

    if text == '🔙 Назад':
        return await start(update, context)

    await update.message.reply_text(response)
    return PARTNERSHIP


# ================== ОБЩИЕ ФУНКЦИИ ================== #
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена операции"""
    await update.message.reply_text(
        "Действие отменено",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


def main() -> None:
    """Запуск бота"""
    application = Application.builder().token("7610154832:AAE5f3cgn0fx9yZGXV8ctlRl0lwCXaOc2to").build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu)],
            FILL_FORM: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answers)],
            PARTNERSHIP: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_partnership)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True
    )

    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(lambda update, ctx: None))  # Для инлайн кнопок

    application.run_polling()


if __name__ == '__main__':
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    main()
