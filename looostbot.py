import os
import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    CallbackContext
)

# Настройка логгирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Глобальные переменные
subscribers = set()

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    subscribers.add(user_id)
    await update.message.reply_text(
        "Привет! Я буду спрашивать, как у тебя дела.\n"
        "Используй команду /rate, чтобы оценить свое состояние от 1 до 5."
    )

# Обработчик команды /rate
async def ask_for_rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[str(i)] for i in range(1, 6)]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    await update.message.reply_text(
        "Как твое состояние сегодня? Оцени от 1 до 5:",
        reply_markup=reply_markup
    )

# Обработка ответа пользователя
async def handle_rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rating = update.message.text
    if rating not in ['1', '2', '3', '4', '5']:
        await update.message.reply_text("Пожалуйста, выбери оценку от 1 до 5")
        return
    
    user = update.effective_user
    logger.info(f"Пользователь {user.id} оценил свое состояние на {rating}")
    await update.message.reply_text(f"Спасибо за оценку {rating}! Можешь оценить снова через /rate")

# Запуск бота
def main():
    # Создаем приложение
    application = Application.builder() \
        .token(os.environ['TOKEN']) \
        .build()
    
    # Регистрируем обработчики
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('rate', ask_for_rating))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_rating))
    
    # Запускаем бота
    application.run_polling()

if __name__ == '__main__':
    main()
