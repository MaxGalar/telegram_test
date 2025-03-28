import os
import logging
from datetime import time
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters
)

# Настройка логгирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я буду ежедневно в 12:00 спрашивать, как у тебя дела.\n"
        "Оценивай свое состояние от 1 до 5."
    )
    
    # Добавляем пользователя в список подписчиков
    user_id = update.effective_user.id
    if 'subscribers' not in context.bot_data:
        context.bot_data['subscribers'] = set()
    context.bot_data['subscribers'].add(user_id)
    
    await send_rating_request(context)

# Отправка запроса на оценку
async def send_rating_request(context: ContextTypes.DEFAULT_TYPE):
    if 'subscribers' not in context.bot_data:
        return
        
    keyboard = [[str(i)] for i in range(1, 6)]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    
    for user_id in context.bot_data['subscribers']:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="Как твое состояние сегодня? Оцени от 1 до 5:",
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения пользователю {user_id}: {e}")

# Обработка ответа пользователя
async def handle_rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rating = update.message.text
    if rating not in ['1', '2', '3', '4', '5']:
        await update.message.reply_text("Пожалуйста, выбери оценку от 1 до 5")
        return
    
    user = update.effective_user
    logger.info(f"Пользователь {user.id} оценил свое состояние на {rating}")
    
    # Здесь можно сохранить оценку в базу данных
    await update.message.reply_text(
        f"Спасибо за оценку! Ты поставил {rating}.\n"
        "Завтра я спрошу снова в 12:00."
    )

# Настройка ежедневного опроса
def setup_daily_job(application):
    # Устанавливаем время опроса (12:00 по UTC+3)
    time_utc = time(hour=9, minute=0)  # 12:00 MSK = 09:00 UTC
    
    # Добавляем задание
    job_queue = application.job_queue
    job_queue.run_daily(send_rating_request, time=time_utc)

# Запуск бота
def main():
    # Создаем приложение
    application = Application.builder() \
        .token(os.environ['TOKEN']) \
        .build()
    
    # Регистрируем обработчики
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_rating))
    
    # Настраиваем ежедневное задание
    setup_daily_job(application)
    
    # Запускаем бота
    application.run_polling()

if __name__ == '__main__':
    main()
