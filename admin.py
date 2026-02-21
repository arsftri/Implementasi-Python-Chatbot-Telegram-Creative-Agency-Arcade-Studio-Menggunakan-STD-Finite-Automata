# admindin.py
# Admin bot untuk A-Design: menerima pesan dari customerbot dan mengirim balasan/link file.

import logging
import json
import os
import requests

from telegram import Update
from telegram.ext import (
    Updater,
    CallbackContext,
    MessageHandler,
    Filters,
    CommandHandler
)

# ==============================
# KONFIGURASI
# ==============================

CUSTOMER_BOT_TOKEN = "8191480802:AAFxihR4I7t8n7oMt7SOw7tbjKsQj2q4Rkw"
ADMIN_BOT_TOKEN = "8542993028:AAG5WbTWXQIttm2ZQCQrd1x9hOAHQlzTFPY"

INVOICE_FILE = "invoices.json"

logging.basicConfig(level=logging.INFO)


# ==============================
# INVOICE HELPERS
# ==============================

def load_invoices():
    if not os.path.exists(INVOICE_FILE):
        return []
    try:
        with open(INVOICE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []


def save_invoices(data):
    with open(INVOICE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def find_invoice(invoice_id):
    invoices = load_invoices()
    for inv in invoices:
        if inv.get("invoice_id") == invoice_id:
            return inv
    return None


def update_invoice(invoice_id, key, value):
    invoices = load_invoices()
    changed = False

    for inv in invoices:
        if inv.get("invoice_id") == invoice_id:
            inv[key] = value
            changed = True
            break

    if changed:
        save_invoices(invoices)
        return True
    return False


# ==============================
# SEND MESSAGE → USER
# ==============================

def send_to_user(user_id, text):
    """Kirim pesan ke pelanggan melalui CUSTOMER BOT."""
    url = f"https://api.telegram.org/bot{CUSTOMER_BOT_TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": user_id,
        "text": text,
        "parse_mode": "Markdown",
    })


# ==============================
# COMMAND: /paid
# ==============================

def cmd_paid(update: Update, context: CallbackContext):
    if len(context.args) == 0:
        update.message.reply_text("Format: /paid <invoice_id>")
        return

    invoice_id = context.args[0]
    inv = find_invoice(invoice_id)
    if not inv:
        update.message.reply_text("Invoice tidak ditemukan.")
        return

    update_invoice(invoice_id, "status", "PAID")

    update.message.reply_text(f"Invoice {invoice_id} sudah ditandai sebagai PAID.")
    send_to_user(inv["user_id"], f"Invoice *{invoice_id}* sudah dikonfirmasi admin. Terima kasih! 😊")


# ==============================
# COMMAND: /sendlink
# ==============================

def cmd_sendlink(update: Update, context: CallbackContext):
    """
    Format:
        /sendlink INV-2025-0009 <link>
    """
    if len(context.args) < 2:
        update.message.reply_text("Format: /sendlink <invoice_id> <link>")
        return

    invoice_id = context.args[0]
    link = context.args[1]

    inv = find_invoice(invoice_id)
    if not inv:
        update.message.reply_text("Invoice tidak ditemukan.")
        return

    # simpan link ke invoice
    update_invoice(invoice_id, "delivery_link", link)
    update_invoice(invoice_id, "status", "DELIVERED")

    # kirim ke user
    send_to_user(inv["user_id"],
        f"📁 *Hasil desain sudah siap!*\n"
        f"Silakan download melalui link berikut:\n\n👉 {link}"
    )

    update.message.reply_text(f"Link untuk invoice {invoice_id} sudah dikirim ke user.")

def admin_media_message(update: Update, context: CallbackContext):
    if not update.message.reply_to_message:
        update.message.reply_text("Kirim file dengan *reply* ke pesan user.")
        return

    user_id = extract_user_id_from_reply(update.message)
    if not user_id:
        update.message.reply_text("User ID tidak ditemukan.")
        return

    bot_token = CUSTOMER_BOT_TOKEN

    # ======================
    # DOKUMEN (PDF / ZIP / PSD / dll)
    # ======================
    if update.message.document:
        file_id = update.message.document.file_id
        url = f"https://api.telegram.org/bot{bot_token}/sendDocument"
        requests.post(url, data={
            "chat_id": user_id,
            "document": file_id,
            "caption": "📁 *Hasil desain sudah siap!*",
            "parse_mode": "Markdown"
        })
        update.message.reply_text("File berhasil dikirim ke user.")
        return

    # ======================
    # FOTO
    # ======================
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
        requests.post(url, data={
            "chat_id": user_id,
            "photo": file_id,
            "caption": "🖼️ *Hasil desain sudah siap!*",
            "parse_mode": "Markdown"
        })
        update.message.reply_text("Foto berhasil dikirim ke user.")
        return

    # ======================
    # VIDEO (MP4)
    # ======================
    if update.message.video:
        file_id = update.message.video.file_id
        url = f"https://api.telegram.org/bot{bot_token}/sendVideo"
        requests.post(url, data={
            "chat_id": user_id,
            "video": file_id,
            "caption": "🎬 *Hasil desain sudah siap!*",
            "parse_mode": "Markdown"
        })
        update.message.reply_text("Video berhasil dikirim ke user.")
        return

# ==============================
# COMMAND: /done
# ==============================

def cmd_done(update: Update, context: CallbackContext):
    if len(context.args) == 0:
        update.message.reply_text("Format: /done <invoice_id>")
        return

    invoice_id = context.args[0]
    inv = find_invoice(invoice_id)

    if not inv:
        update.message.reply_text("Invoice tidak ditemukan.")
        return

    update_invoice(invoice_id, "status", "COMPLETED")

    update.message.reply_text(f"Order {invoice_id} ditutup.")
    send_to_user(inv["user_id"],
        f"✨ Order *{invoice_id}* telah selesai.\n"
        f"Terima kasih sudah menggunakan layanan ArcadeStudioBot! 😊"
        f"Ketik */start* untuk melakukan pemesanan kembali 🚀"
    )


# ==============================
# EXTRACT USER ID FROM REPLY
# ==============================

def extract_user_id_from_reply(message):
    if not message.reply_to_message:
        return None

    replied = message.reply_to_message

    original_text = replied.text or replied.caption
    if not original_text:
        return None

    if original_text.startswith("[USER"):
        try:
            return int(original_text.split()[1].replace("]", ""))
        except:
            return None

    return None



# ==============================
# HANDLE ADMIN REPLY (TEXT — LINK)
# ==============================

def admin_message(update: Update, context: CallbackContext):
    """
    Kalau admin reply pesan user dan menulis sebuah LINK,
    bot otomatis kirim ke user.
    """

    if update.message.reply_to_message:
        user_id = extract_user_id_from_reply(update.message)
        if not user_id:
            update.message.reply_text("Tidak dapat membaca user_id dari pesan reply.")
            return

        text = update.message.text.strip()

        # Jika admin mengirim LINK (hasil desain)
        if text.startswith("http://") or text.startswith("https://"):
            send_to_user(
                user_id,
                f"📁 *Hasil desain sudah siap!*\n"
                f"Silakan review melalui link berikut:\n\n👉 {text}\n\n"
                f"Note:\n"
                f"Jika ingin revisi, reply pesan ini dan ketik *revisi*\n"
                f"Jika tidak ingin revisi, reply pesan ini dan ketik *puas*"
            )
            update.message.reply_text("Link telah dikirim ke user.")
            return

        # Jika hanya pesan biasa
        send_to_user(user_id, f"(Admin): {text}")
        return

    update.message.reply_text(
        "Balas pesan user dengan *reply* agar tersambung.",
        parse_mode="Markdown",
    )


# ==============================
# MAIN
# ==============================

def main():
    updater = Updater(ADMIN_BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("paid", cmd_paid))
    dp.add_handler(CommandHandler("sendlink", cmd_sendlink))
    dp.add_handler(CommandHandler("done", cmd_done))
    dp.add_handler(MessageHandler(
        Filters.document | Filters.photo | Filters.video,
        admin_media_message
    ))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, admin_message))

    print("Admin Bot berjalan…")
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()