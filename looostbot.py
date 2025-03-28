import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Привет, {update.effective_user.first_name}!\n"
        "Сегодня замечательный день! ☀️"
    )

def main():
    # Создаем приложение
    app = Application.builder().token(os.environ['TOKEN']).build()
    
    # Добавляем обработчик команды /start
    app.add_handler(CommandHandler('start', start))
    
    # Запускаем бота
    app.run_polling()

if __name__ == '__main__':
    main()
