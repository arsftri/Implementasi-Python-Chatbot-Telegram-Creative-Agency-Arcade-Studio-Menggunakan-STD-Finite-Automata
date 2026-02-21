from telegram.ext import Updater, MessageHandler, Filters

TOKEN = "8542993028:AAG5WbTWXQIttm2ZQCQrd1x9hOAHQlzTFPY"

def get_id(update, context):
    chat = update.message.chat
    update.message.reply_text(f"Your chat_id is: {chat.id}")
    print(f"chat_id: {chat.id}")

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(MessageHandler(Filters.text, get_id))

    print("Bot berjalan, silakan chat bot ini…")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()