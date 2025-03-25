import datetime
import os
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# TOKEN = "8161011333:AAFpt-URWfP2YIJWHBO43_InCSOmJyxMUcU"  # Замените на реальный токен от @BotFather
TOKEN = os.environ['TOKEN']

# --- Клавиатура с кнопками ---
def get_keyboard() -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton("🕒 Текущее время")],
        [KeyboardButton("🚪 Остановить бота")],
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

# --- Обработчики команд ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет! Выбери действие:",
        reply_markup=get_keyboard(),
    )

async def show_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    current_time = datetime.datetime.now().strftime("%H:%M:%S %d.%m.%Y")
    await update.message.reply_text(f"⏰ Текущее время: {current_time}")

async def stop_bot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Бот завершает работу...", reply_markup=None)
    await context.application.stop()  # Корректное завершение для PTB v20+

# --- Запуск бота ---
def main() -> None:
    application = Application.builder().token(TOKEN).build()

    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Regex("^🕒 Текущее время$"), show_time))
    application.add_handler(MessageHandler(filters.Regex("^🚪 Остановить бота$"), stop_bot))

    print("Бот запущен...")
    application.run_polling()

if __name__ == "__main__":
    main()
