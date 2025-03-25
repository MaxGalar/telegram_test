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
        parsed = urlparse(db_url)
        
        conn = psycopg2.connect(
            dbname=parsed.path[1:],
            user=parsed.username,
            password=parsed.password,
            host=parsed.hostname,
            port=parsed.port,
            sslmode='require'
        )
        return conn
    except Exception as e:
        logger.error(f"Ошибка подключения к БД: {str(e)}")
        raise

# --- Инициализация БД ---
def init_db():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Создаем таблицу, если не существует
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_actions (
                        user_id BIGINT PRIMARY KEY,
                        first_activity TIMESTAMP DEFAULT NOW(),
                        last_activity TIMESTAMP DEFAULT NOW(),
                        actions_count INTEGER DEFAULT 1,
                        username TEXT
                    )
                """)
                
                # Проверяем наличие столбца username
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='user_actions' AND column_name='username'
                """)
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE user_actions ADD COLUMN username TEXT")
                
                conn.commit()
                logger.info("Таблица user_actions готова к работе")
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
                """, (user_id, username, username))
                conn.commit()
                logger.info(f"Действие пользователя {user_id} записано в БД")
    except Exception as e:
        logger.error(f"Ошибка записи в БД: {str(e)}")

# --- Получение статистики ---
async def get_user_stats(user_id: int):
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
    await log_action(user.id, user.username)
    await update.message.reply_text(
        f"Привет, {user.first_name}! Выбери действие:",
        reply_markup=get_keyboard()
    )

async def show_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await log_action(user.id)
    current_time = datetime.datetime.now().strftime("%H:%M:%S %d.%m.%Y")
    await update.message.reply_text(f"⏰ Текущее время: {current_time}")

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    stats = await get_user_stats(user.id)
    
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
    required_vars = ['DATABASE_URL', 'TOKEN']
    missing_vars = [var for var in required_vars if var not in os.environ]
    
    if missing_vars:
        logger.error(f"Отсутствуют переменные окружения: {', '.join(missing_vars)}")
        return
    
    # Инициализация БД
    init_db()
    
    # Создание приложения
    app = Application.builder().token(os.environ['TOKEN']).build()
    
    # Регистрация обработчиков
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.Regex('^🕒 Текущее время$'), show_time))
    app.add_handler(MessageHandler(filters.Regex('^📊 Моя статистика$'), show_stats))
    app.add_handler(MessageHandler(filters.Regex('^🚪 Остановить бота$'), stop_bot))
    
    logger.info("Бот запущен и готов к работе")
    app.run_polling()

if __name__ == '__main__':
    main()
