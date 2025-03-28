import os
import logging
import asyncio
from datetime import datetime, time
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

# Хранилище данных (временное, для продакшена лучше использовать БД)
subscribers = set()

# Отправка опроса всем подписчикам
async def send_daily_poll(app: Application):
    if not subscribers:
        logger.info("Нет активных подписчиков")
        return

    keyboard = [[str(i)] for i in range(1, 6)]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)

    for user_id in subscribers:
        try:
            await app.bot.send_message(
                chat_id=user_id,
                text="Как твое состояние сегодня? Оцени от 1 до 5:",
                reply_markup=reply_markup
            )
            logger.info(f"Опрос отправлен пользователю {user_id}")
        except Exception as e:
            logger.error(f"Ошибка отправки для {user_id}: {e}")

# Фоновая задача для ежедневных опросов
async def daily_poll_scheduler(app: Application):
    while True:
        now = datetime.utcnow().time()
        target_time = time(hour=9, minute=0)  # 12:00 МСК = 09:00 UTC
        
        # Если текущее время совпадает с целевым (±1 минута)
        if now.hour == target_time.hour and abs(now.minute - target_time.minute) <= 1:
            await send_daily_poll(app)
            await asyncio.sleep(60)  # Защита от повторного срабатывания
        else:
            await asyncio.sleep(30)  # Проверяем каждые 30 секунд

# Обработчики команд
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    subscribers.add(user_id)
    await update.message.reply_text(
        "Привет! Я буду присылать тебе ежедневный опрос в 12:00 по МСК.\n"
        "Сегодняшний опрос: /rate"
    )
    logger.info(f"Новый подписчик: {user_id}")

async def manual_rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[str(i)] for i in range(1, 6)]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    await update.message.reply_text(
        "Оцени свое состояние сейчас:",
        reply_markup=reply_markup
    )

async def handle_rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rating = update.message.text
    if rating not in ['1', '2', '3', '4', '5']:
        await update.message.reply_text("Пожалуйста, выбери оценку от 1 до 5")
        return
    
    user = update.effective_user
    logger.info(f"Пользователь {user.id} оценил состояние на {rating}")
    await update.message.reply_text(f"Спасибо за оценку {rating}!")

# Запуск бота
def main():
    # Проверка токена
    if 'TOKEN' not in os.environ:
        logger.error("Не задан BOT_TOKEN")
        return

    # Создаем приложение
    application = Application.builder() \
        .token(os.environ['TOKEN']) \
        .build()

    # Регистрируем обработчики
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('rate', manual_rate))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_rating))

    # Запускаем фоновую задачу
    application.job_queue.run_once(
        lambda _: asyncio.create_task(daily_poll_scheduler(application)),
        when=1
    )

    logger.info("Бот запущен с ежедневными опросами в 12:00 МСК")
    application.run_polling()

if __name__ == '__main__':
    main()
