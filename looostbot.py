import datetime
import os
import logging
import psycopg2
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- Настройка логгирования ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),  # Логи в файл
        logging.StreamHandler()          # Логи в консоль
    ]
)
logger = logging.getLogger(__name__)

# --- Подключение к PostgreSQL (Railway) ---
def get_db_connection():
    return psycopg2.connect(
        dbname=os.environ['PGDATABASE'],
        user=os.environ['PGUSER'],
        password=os.environ['PGPASSWORD'],
        host=os.environ['PGHOST'],
        port=os.environ['PGPORT']
    )

# --- Инициализация БД ---
def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_actions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT NOW()
            )
        ''')
        conn.commit()
        logger.info("База данных инициализирована")
    except Exception as e:
        logger.error(f"Ошибка инициализации БД: {e}")
    finally:
        if conn:
            conn.close()

# --- Логирование действий в БД ---
async def log_action(user_id: int, action: str):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO user_actions (user_id, action) VALUES (%s, %s)',
            (user_id, action)
        conn.commit()
    except Exception as e:
        logger.error(f"Ошибка записи в БД: {e}")
    finally:
        if conn:
            conn.close()

# --- Клавиатура ---
def get_keyboard() -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton("🕒 Текущее время")],
        [KeyboardButton("📊 Моя статистика")],  # Новая кнопка
        [KeyboardButton("🚪 Остановить бота")],
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

# --- Обработчики команд ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info(f"Пользователь {user.id} запустил бота")
    await log_action(user.id, "start")
    await update.message.reply_text(
        f"Привет, {user.first_name}! Выбери действие:",
        reply_markup=get_keyboard(),
    )

async def show_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info(f"Пользователь {user.id} запросил время")
    await log_action(user.id, "time_request")
    current_time = datetime.datetime.now().strftime("%H:%M:%S %d.%m.%Y")
    await update.message.reply_text(f"⏰ Текущее время: {current_time}")

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT COUNT(*) FROM user_actions WHERE user_id = %s',
            (user.id,)
        )
        count = cursor.fetchone()[0]
        await update.message.reply_text(
            f"📊 Вы использовали бота {count} раз(а)"
        )
        await log_action(user.id, "stats_request")
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        await update.message.reply_text("⚠️ Не удалось получить статистику")
    finally:
        if conn:
            conn.close()

async def stop_bot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info(f"Пользователь {user.id} остановил бота")
    await log_action(user.id, "bot_stop")
    await update.message.reply_text("Бот завершает работу...", reply_markup=None)
    await context.application.stop()

# --- Запуск бота ---
def main() -> None:
    # Инициализация БД
    init_db()
    
    # Создание приложения
    application = Application.builder().token(os.environ['TOKEN']).build()

    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Regex("^🕒 Текущее время$"), show_time))
    application.add_handler(MessageHandler(filters.Regex("^📊 Моя статистика$"), show_stats))
    application.add_handler(MessageHandler(filters.Regex("^🚪 Остановить бота$"), stop_bot))

    logger.info("Бот запускается...")
    application.run_polling()

if __name__ == "__main__":
    main()
