import os
import logging
from datetime import time
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

# Глобальное хранилище подписчиков (в продакшене лучше использовать БД)
subscribers = set()

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    subscribers.add(user_id)
    await update.message.reply_text(
        "Привет! Я буду присылать тебе ежедневный опрос в 12:00 по МСК.\n"
        "Оценивай свое состояние от 1 до 5."
    )
    logger.info(f"Новый подписчик: {user_id}")

# Отправка опроса всем подписчикам
async def send_daily_poll(context: CallbackContext):
    if not subscribers:
        logger.info("Нет подписчиков для опроса")
        return
    
    keyboard = [[str(i)] for i in range(1, 6)]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    
    for user_id in subscribers:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="Как твое состояние сегодня? Оцени от 1 до 5:",
                reply_markup=reply_markup
            )
            logger.info(f"Опрос отправлен пользователю {user_id}")
        except Exception as e:
            logger.error(f"Ошибка отправки пользователю {user_id}: {e}")

# Обработка ответа на опрос
async def handle_rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rating = update.message.text
    user = update.effective_user
    
    if rating not in ['1', '2', '3', '4', '5']:
        await update.message.reply_text("Пожалуйста, выбери оценку от 1 до 5")
        return
    
    logger.info(f"Пользователь {user.id} оценил состояние на {rating}")
    await update.message.reply_text(f"Спасибо за оценку {rating}! Завтра спрошу снова в 12:00")

# Настройка ежедневного задания
def setup_job_queue(application):
    # 12:00 по МСК = 09:00 UTC
    job_queue = application.job_queue
    job_queue.run_daily(
        send_daily_poll,
        time=time(hour=9, minute=0, second=0),  # 09:00 UTC
        days=(0, 1, 2, 3, 4, 5, 6),  # Все дни недели
        name="daily_poll"
    )

# Запуск бота
def main():
    # Создаем приложение с включенным JobQueue
    application = Application.builder() \
        .token(os.environ['TOKEN']) \
        .build()
    
    # Регистрируем обработчики
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_rating))
    
    # Настраиваем ежедневный опрос
    setup_job_queue(application)
    
    # Запускаем бота
    logger.info("Бот запущен и готов к работе")
    application.run_polling()

if __name__ == '__main__':
    main()
