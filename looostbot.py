import os
import asyncpg # Добавили импорт asyncpg
import logging # Добавили импорт logging для вывода ошибок
from datetime import datetime # Для сохранения времени

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# --- Настройка логирования (рекомендуется) ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)
# --------------------------------------------

# --- Функция для инициализации БД (создание таблицы) ---
# Эту функцию можно вызвать один раз при старте или проверять/создавать таблицу при каждом подключении
async def ensure_user_table_exists(conn):
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS bot_users (
            user_id BIGINT PRIMARY KEY,
            first_name TEXT,
            username TEXT,
            started_at TIMESTAMP WITH TIME ZONE
        )
    ''')
# --------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    first_name = user.first_name
    username = user.username # Может быть None

    logger.info(f"Пользователь {first_name} (ID: {user_id}) запустил бота.")

    # --- Работа с базой данных ---
    conn = None # Инициализируем conn как None
    try:
        # Получаем строку подключения из переменных окружения (Railway ее предоставит)
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
             logger.error("Переменная окружения DATABASE_URL не найдена!")
             await update.message.reply_text(
                f"Привет, {first_name}! Что-то пошло не так с подключением к базе."
             )
             return # Выходим, если нет строки подключения

        # Подключаемся к БД
        conn = await asyncpg.connect(database_url)

        # Убедимся, что таблица существует (можно вынести в main, но так проще для старта)
        await ensure_user_table_exists(conn)

        # Сохраняем или обновляем пользователя
        # Используем INSERT ... ON CONFLICT (UPSERT)
        await conn.execute('''
            INSERT INTO bot_users (user_id, first_name, username, started_at)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_id) DO UPDATE SET
                first_name = EXCLUDED.first_name,
                username = EXCLUDED.username,
                started_at = EXCLUDED.started_at
        ''', user_id, first_name, username, datetime.now()) # Используем текущее время

        logger.info(f"Данные пользователя {first_name} (ID: {user_id}) сохранены/обновлены в БД.")

        await update.message.reply_text(
            f"Привет, {first_name}!\n"
            "Сегодня замечательный день! ☀️\n"
            "Я записал тебя в базу данных!"
        )

    except asyncpg.PostgresError as e:
        logger.error(f"Ошибка при работе с PostgreSQL: {e}")
        await update.message.reply_text(
            f"Привет, {first_name}! Произошла ошибка при сохранении данных."
        )
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")
        await update.message.reply_text(
             f"Привет, {first_name}! Произошла непредвиденная ошибка."
        )
    finally:
        # Важно: всегда закрывать соединение
        if conn:
            await conn.close()
            logger.debug("Соединение с БД закрыто.")
    # -----------------------------

def main():
    # Получаем токен бота
    bot_token = os.environ.get('TOKEN')
    if not bot_token:
        logger.critical("Переменная окружения TOKEN не найдена! Бот не может быть запущен.")
        return # Выход, если нет токена

    # Создаем приложение
    app = Application.builder().token(bot_token).build()

    # Добавляем обработчик команды /start
    app.add_handler(CommandHandler('start', start))

    logger.info("Запуск бота...")
    # Запускаем бота
    app.run_polling()

if __name__ == '__main__':
    main()
