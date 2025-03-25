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

# --- Подключение к PostgreSQL ---
def get_db_connection():
    try:
        db_url = os.environ['DATABASE_URL']
        logger.info(f"Подключаемся к БД с URL: {db_url[:15]}...")  # Логируем часть URL для безопасности
        
        parsed = urlparse(db_url)
        conn = psycopg2.connect(
            dbname=parsed.path[1:],
            user=parsed.username,
            password=parsed.password,
            host=parsed.hostname,
            port=parsed.port,
            sslmode='require'
        )
        logger.info("Успешное подключение к БД")
        return conn
    except Exception as e:
        logger.error(f"Ошибка подключения к БД: {str(e)}")
        raise

# --- Инициализация БД ---
def init_db():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_actions (
                        user_id BIGINT PRIMARY KEY,
                        username TEXT,
                        first_activity TIMESTAMP DEFAULT NOW(),
                        last_activity TIMESTAMP DEFAULT NOW(),
                        actions_count INTEGER DEFAULT 1
                    )
                """)
                conn.commit()
                logger.info("Таблица user_actions создана/проверена")
                
                # Проверка существования данных
                cursor.execute("SELECT COUNT(*) FROM user_actions")
                count = cursor.fetchone()[0]
                logger.info(f"В таблице {count} записей")
    except Exception as e:
        logger.error(f"Ошибка инициализации БД: {str(e)}")
        raise

# --- Логирование действий ---
async def log_action(user_id: int, username: str = None):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO user_actions (user_id, username)
                    VALUES (%s, %s)
                    ON CONFLICT (user_id) DO UPDATE SET
                        last_activity = NOW(),
                        actions_count = user_actions.actions_count + 1,
                        username = COALESCE(%s, user_actions.username)
                    RETURNING actions_count
                """, (user_id, username, username))
                conn.commit()
                result = cursor.fetchone()
                logger.info(f"Запись в БД: user_id={user_id}, actions_count={result[0] if result else 'N/A'}")
    except Exception as e:
        logger.error(f"Ошибка записи в БД: {str(e)}")

# --- Получение статистики ---
async def get_stats(user_id: int):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT first_activity, last_activity, actions_count
                    FROM user_actions
                    WHERE user_id = %s
                """, (user_id,))
                return cursor.fetchone()
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {str(e)}")
        return None

# --- Клавиатура ---
def get_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("🕒 Текущее время")],
        [KeyboardButton("📊 Моя статистика")],
        [KeyboardButton("🚪 Остановить бота")]
    ], resize_keyboard=True)

# --- Обработчики команд ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"Старт от {user.id}")
    await log_action(user.id, user.username)
    await update.message.reply_text(
        f"Привет, {user.first_name}! Выбери действие:",
        reply_markup=get_keyboard()
    )

async def show_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await log_action(user.id)
    time_str = datetime.datetime.now().strftime("%H:%M:%S %d.%m.%Y")
    await update.message.reply_text(f"⏰ Текущее время: {time_str}")

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    stats = await get_stats(user.id)
    
    if stats:
        first, last, count = stats
        message = (
            f"📊 Ваша статистика:\n"
            f"• Первый визит: {first.strftime('%d.%m.%Y %H:%M')}\n"
            f"• Последний визит: {last.strftime('%d.%m.%Y %H:%M')}\n"
            f"• Всего действий: {count}"
        )
    else:
        message = "📊 Статистика не найдена"
    
    await update.message.reply_text(message)

async def stop_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот завершает работу...")
    await context.application.stop()

# --- Запуск бота ---
def main():
    # Проверка переменных окружения
    for var in ['DATABASE_URL', 'TOKEN']:
        if var not in os.environ:
            logger.error(f"Отсутствует переменная окружения: {var}")
            return
    
    init_db()  # Инициализация БД с логированием
    
    app = Application.builder().token(os.environ['TOKEN']).build()
    
    # Регистрация обработчиков
    handlers = [
        CommandHandler('start', start),
        MessageHandler(filters.Regex('^🕒 Текущее время$'), show_time),
        MessageHandler(filters.Regex('^📊 Моя статистика$'), show_stats),
        MessageHandler(filters.Regex('^🚪 Остановить бота$'), stop_bot)
    ]
    
    for handler in handlers:
        app.add_handler(handler)
    
    logger.info("Бот запущен и готов к работе")
    app.run_polling()

if __name__ == '__main__':
    main()
