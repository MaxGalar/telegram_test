import datetime
import os
import logging
import psycopg2
from urllib.parse import urlparse
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- Настройка логгирования ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Подключение к PostgreSQL через DATABASE_URL ---
def get_db_connection():
    db_url = os.environ['DATABASE_URL']
    parsed = urlparse(db_url)
    
    return psycopg2.connect(
        dbname=parsed.path[1:],  # Убираем первый символ '/'
        user=parsed.username,
        password=parsed.password,
        host=parsed.hostname,
        port=parsed.port,
        sslmode='require'
    )

# --- Инициализация БД ---
def init_db():
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_actions (
                user_id SERIAL PRIMARY KEY,
                first_activity TIMESTAMP DEFAULT NOW(),
                last_activity TIMESTAMP DEFAULT NOW(),
                actions_count INTEGER DEFAULT 1
            )
        """)
        conn.commit()
        logger.info("База данных инициализирована")
    except Exception as e:
        logger.error(f"Ошибка инициализации БД: {e}")
        raise
    finally:
        if conn:
            conn.close()

# --- Клавиатура ---
def get_keyboard() -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton("🕒 Текущее время")],
        [KeyboardButton("📊 Моя статистика")],
        [KeyboardButton("🚪 Остановить бота")],
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

# --- Логирование действий ---
async def log_action(user_id: int):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO user_actions (user_id)
            VALUES (%s)
            ON CONFLICT (user_id) DO UPDATE SET
                last_activity = NOW(),
                actions_count = user_actions.actions_count + 1
        """, (user_id,))
        conn.commit()
    except Exception as e:
        logger.error(f"Ошибка записи в БД: {e}")
    finally:
        if conn:
            conn.close()

# --- Обработчики команд ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info(f"Пользователь {user.id} запустил бота")
    await log_action(user.id)
    await update.message.reply_text(
        f"Привет, {user.first_name}! Выбери действие:",
        reply_markup=get_keyboard(),
    )

async def show_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info(f"Пользователь {user.id} запросил время")
    await log_action(user.id)
    current_time = datetime.datetime.now().strftime("%H:%M:%S %d.%m.%Y")
    await update.message.reply_text(f"⏰ Текущее время: {current_time}")

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await log_action(user.id)
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT first_activity, last_activity, actions_count
            FROM user_actions
            WHERE user_id = %s
        """, (user.id,))
        
        result = cursor.fetchone()
        if result:
            first_activity, last_activity, count = result
            first_str = first_activity.strftime("%d.%m.%Y %H:%M")
            last_str = last_activity.strftime("%d.%m.%Y %H:%M")
            message = (
                f"📊 Ваша статистика:\n"
                f"• Первый визит: {first_str}\n"
                f"• Последний визит: {last_str}\n"
                f"• Всего действий: {count}"
            )
        else:
            message = "📊 Статистика не найдена"
        
        await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        await update.message.reply_text("⚠️ Не удалось получить статистику")
    finally:
        if conn:
            conn.close()

async def stop_bot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info(f"Пользователь {user.id} остановил бота")
    await log_action(user.id)
    await update.message.reply_text("Бот завершает работу...", reply_markup=None)
    await context.application.stop()

# --- Запуск бота ---
def main() -> None:
    # Проверяем наличие необходимых переменных
    required_vars = ['DATABASE_URL', 'TOKEN']
    missing_vars = [var for var in required_vars if var not in os.environ]
    
    if missing_vars:
        logger.error(f"Отсутствуют переменные окружения: {', '.join(missing_vars)}")
        return
    
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
