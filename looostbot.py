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

# ... (остальные функции остаются без изменений, как в предыдущем коде) ...

def main() -> None:
    # Проверяем наличие DATABASE_URL
    if 'DATABASE_URL' not in os.environ:
        logger.error("Не найдена переменная DATABASE_URL!")
        return
    
    init_db()
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
