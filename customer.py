# customdin.py
# Customer bot untuk A-Design / Layanan Logo Dindaaa

import logging
import json
import os
from datetime import datetime
from io import BytesIO

from matplotlib import text
import requests
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Updater,
    CallbackContext,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    Filters,
)

# ==============================
# KONFIGURASI
# ==============================

CUSTOMER_BOT_TOKEN = "8191480802:AAFxihR4I7t8n7oMt7SOw7tbjKsQj2q4Rkw"
ADMIN_BOT_TOKEN = "8542993028:AAG5WbTWXQIttm2ZQCQrd1x9hOAHQlzTFPY"
ADMIN_CHAT_ID = 5298602480  # chat_id admin

INVOICE_FILE = "invoices.json"


logging.basicConfig(level=logging.INFO)

# ==============================
# HELPER: INVOICE STORAGE
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


def save_rating(invoice_id, rating):
    invoices = load_invoices()
    for inv in invoices:
        if inv.get("invoice_id") == invoice_id:
            inv["rating"] = rating
            break
    save_invoices(invoices)


def create_invoice(user, service_label, unit_price, qty):
    invoices = load_invoices()
    seq = len(invoices) + 1
    year = datetime.now().year
    invoice_id = f"INV-{year}-{seq:04d}"
    total = unit_price * qty

    record = {
        "invoice_id": invoice_id,
        "seq": seq,
        "user_id": user.id,
        "username": user.username or "",
        "full_name": user.full_name,
        "service_label": service_label,
        "unit_price": unit_price,
        "qty": qty,
        "total_price": total,
        "status": "WAITING_PAYMENT",
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }

    invoices.append(record)
    save_invoices(invoices)
    return record


def get_invoice_by_id(invoice_id: str):
    invoices = load_invoices()
    for inv in invoices:
        if inv.get("invoice_id") == invoice_id:
            return inv
    return None


def get_last_invoice_for_user(user_id: int):
    invoices = load_invoices()
    user_invoices = [inv for inv in invoices if inv.get("user_id") == user_id]
    if not user_invoices:
        return None
    return sorted(user_invoices, key=lambda x: x.get("seq", 0))[-1]

# ==============================
# KATALOG LAYANAN & HARGA
# ==============================


ORDER_CATALOG = {
    "order_ui_ux_design": {
        "label": "UI/UX Design",
        "price": 70000,
    },
    "order_company_profile_animation": {
        "label": "Company Profile Animation",
        "price": 70000,
    },
    "order_product_explainer_video": {
        "label": "Product Explainer Video",
        "price": 70000,
    },
    "order_animation": {
        "label": "Animation",
        "price": 70000,
    },
    "order_overlay_stream": {
        "label": "Overlay Stream",
        "price": 70000,
    },
    "order_music_video": {
        "label": "Music Video",
        "price": 70000,
    },
}


PAYMENT_TEXT = (
    "Silakan lakukan pembayaran ke salah satu rekening berikut dengan rentang waktu 24 jam:\n\n"
    "• *BCA* 123456789 a.n. *Kelompok 1*\n"
    "• *Dana* 08123456789 a.n. *Kelompok 1*\n"
    "• *Gopay* 08123456789 a.n. *Kelompok 1*\n"
    "• *OVO* 08123456789 a.n. *Kelompok 1*\n"
)

def main_menu():
    buttons = [
        [InlineKeyboardButton("🎨 UI/UX Design", callback_data="menu_uiux")],
        [InlineKeyboardButton("📱 Company Profile Animation", callback_data="menu_company_profile_animation")],
        [InlineKeyboardButton("🖼 Product Explainer Video", callback_data="menu_product_explainer_video")],
        [InlineKeyboardButton("📊 Animation", callback_data="menu_animation")],
        [InlineKeyboardButton("💼 Overlay Stream", callback_data="menu_overlay_stream")],
        [InlineKeyboardButton("🟦 Music Video", callback_data="menu_music_video")],
    ]
    return InlineKeyboardMarkup(buttons)



# ==============================
# HELPER: MENU
# ==============================


def order_button(order_key: str, back_cb: str):
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(
                "💬 Hubungi Admin untuk Pemesanan",
                callback_data=f"contact_admin|{order_key}"
            )],
            [InlineKeyboardButton("⬅ Kembali", callback_data=back_cb)],
        ]
    )

# ==============================
# HELPER: KIRIM KE ADMIN BOT
# ==============================

def send_text_to_admin(user, text: str):
    """Kirim pesan teks ke admin bot (ADMIN_BOT_TOKEN → ADMIN_CHAT_ID)."""
    url = f"https://api.telegram.org/bot{ADMIN_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": ADMIN_CHAT_ID,
        "text": f"[USER {user.id}] {text}",
    }
    requests.post(url, data=payload)


def notify_new_order_to_admin(user, invoice_record):
    """Kirim detail order baru ke admin."""
    url = f"https://api.telegram.org/bot{ADMIN_BOT_TOKEN}/sendMessage"
    msg = (
        f"[USER {user.id}] 📩 Order baru\n\n"
        f"Invoice : {invoice_record['invoice_id']}\n"
        f"Nama    : {invoice_record['full_name']}\n"
        f"Layanan : {invoice_record['service_label']}\n"
        f"Qty     : {invoice_record['qty']}\n"
        f"Total   : Rp {invoice_record['total_price']:,}".replace(",", ".")
    )
    requests.post(url, data={"chat_id": ADMIN_CHAT_ID, "text": msg})


def forward_media_to_admin(update: Update, context: CallbackContext):
    """Download file dari customer bot, upload ke admin bot."""
    user = update.effective_user
    msg = update.message

    # FOTO
    if msg.photo:
        photo = msg.photo[-1]  # kualitas paling besar
        file_obj = context.bot.get_file(photo.file_id)

        bio = BytesIO()
        bio.name = "payment.jpg"
        file_obj.download(out=bio)
        bio.seek(0)

        files = {"photo": (bio.name, bio)}
        data = {
            "chat_id": ADMIN_CHAT_ID,
            "caption": f"[USER {user.id}] Bukti pembayaran",
        }
        requests.post(
            f"https://api.telegram.org/bot{ADMIN_BOT_TOKEN}/sendPhoto",
            data=data,
            files=files,
        )
        return

    # DOKUMEN (pdf / jpg / png dll)
    if msg.document:
        doc = msg.document
        file_obj = context.bot.get_file(doc.file_id)

        bio = BytesIO()
        filename = doc.file_name or "file"
        file_obj.download(out=bio)
        bio.seek(0)

        files = {"document": (filename, bio)}
        data = {
            "chat_id": ADMIN_CHAT_ID,
            "caption": f"[USER {user.id}] Bukti pembayaran",
        }
        requests.post(
            f"https://api.telegram.org/bot{ADMIN_BOT_TOKEN}/sendDocument",
            data=data,
            files=files,
        )
        return


# ==============================
# START COMMAND
# ==============================

def send_banner(update: Update, context: CallbackContext):
    """Kirim daftar layanan di awal /start tanpa banner."""
    try:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                "*Halo, Arcade Buddy!* 🎨✨\n"
                "*Transform Raw Footage into Memorable Visual Experiences*\n\n"
                "Berikut *Arcade Studio Services* yang tersedia:\n"
                "1️⃣ *UI/UX Design* – Tampilan modern & user-friendly\n"
                "2️⃣ *Company Profile Animation* – Profil bisnis lebih profesional\n"
                "3️⃣ *Product Explainer Video* – Jelaskan produk secara visual & menarik\n"
                "4️⃣ *Animation* – Animasi kreatif sesuai kebutuhan\n"
                "5️⃣ *Overlay Stream* – Tampilan live stream lebih estetik\n"
                "6️⃣ *Music Video* – Visual musik yang engaging\n\n"
            ),
            parse_mode="Markdown",
        )
    except Exception as e:
        logging.warning(f"Gagal kirim pesan layanan: {e}")


def start(update: Update, context: CallbackContext):
    # reset state user
    context.user_data.clear()
    context.user_data["stage"] = None
    context.user_data["admin_mode"] = False
    context.user_data["active_invoice_id"] = None

    send_banner(update, context)

    update.message.reply_text(
        "Silahkan pilih *Arcade Studio Service* yang kamu butuhkan✨",
        parse_mode="Markdown",
        reply_markup=main_menu(),
    )

# ==============================
# CALLBACK HANDLER (BUTTON)
# ==============================

def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    user = query.from_user
    data = query.data
    query.answer()

    # Kembali ke main menu
    if data == "main":
        query.edit_message_text(
            "✨ Silakan pilih layanan:",
            reply_markup=main_menu(),
        )
        return

    # ------------ MENU UI/UX ------------
    if data == "menu_uiux":
        context.user_data["selected_service"] = "UI/UX Design"
        query.edit_message_text(
            text=(
                "🎨 *UI/UX Design*\n\n"
                "Detail Layanan:\n\n"

                "*Tingkat Kesulitan 1*\n"
                "• Wireframe & visual design\n"
                "• 1 halaman (single screen)\n"
                "• Revisi hingga 2x\n"
                "• File PNG / JPG / Figma\n"
                "💰 *Harga: Rp 70.000*\n\n"

                "*Tingkat Kesulitan 2*\n"
                "• Wireframe & visual design\n"
                "• 2 halaman (multi screen sederhana)\n"
                "• Revisi hingga 2x\n"
                "• File PNG / JPG / Figma\n"
                "💰 *Harga: Rp 80.000*\n\n"

                "*Tingkat Kesulitan 3*\n"
                "• User flow sederhana\n"
                "• 3–4 halaman\n"
                "• Konsistensi warna & komponen\n"
                "• Revisi hingga 3x\n"
                "• File PNG / JPG / Figma\n"
                "💰 *Harga: Rp 90.000*\n\n"

                "*Tingkat Kesulitan 4*\n"
                "• User flow lengkap\n"
                "• 5–7 halaman\n"
                "• Komponen reusable (design system dasar)\n"
                "• Revisi hingga 3x\n"
                "• File PNG / JPG / Figma\n"
                "💰 *Harga: Rp 95.000*\n\n"

                "*Tingkat Kesulitan 5*\n"
                "• UX research ringan\n"
                "• 8–10 halaman\n"
                "• Design system konsisten\n"
                "• Prototype interaktif\n"
                "• Revisi hingga 4x\n"
                "• File PNG / JPG / Figma\n"
                "💰 *Harga: Rp 99.999*\n\n"

                "Jika ingin melanjutkan pemesanan,\n"
                "silakan hubungi admin 😊"
            ),
            parse_mode="Markdown",
            reply_markup=order_button(
                "order_ui_ux_design",
                "main"
            ),
        )
        return

    # ------------ MENU COMPANY PROFILE ANIMATION ------------
    if data == "menu_company_profile_animation":
        context.user_data["selected_service"] = "Company Profile Animation"
        query.edit_message_text(
            text=(
                "📱 *Company Profile Animation*\n\n"
                "Detail Layanan:\n\n"

                "*Tingkat Kesulitan 1*\n"
                "• Animasi teks & logo sederhana\n"
                "• Durasi ±1 menit\n"
                "• Transisi dasar\n"
                "• Revisi hingga 1x\n"
                "• Format MP4\n"
                "💰 *Harga: Rp 70.000*\n\n"

                "*Tingkat Kesulitan 2*\n"
                "• Animasi teks & visual sederhana\n"
                "• Durasi 1–2 menit\n"
                "• Transisi smooth\n"
                "• Revisi hingga 1x\n"
                "• Format MP4\n"
                "💰 *Harga: Rp 80.000*\n\n"

                "*Tingkat Kesulitan 3*\n"
                "• Visual storytelling sederhana\n"
                "• Durasi 2–3 menit\n"
                "• Animasi ikon & ilustrasi\n"
                "• Background music\n"
                "• Revisi hingga 2x\n"
                "• Format MP4\n"
                "💰 *Harga: Rp 90.000*\n\n"

                "*Tingkat Kesulitan 4*\n"
                "• Storyboard terstruktur\n"
                "• Durasi 3–5 menit\n"
                "• Motion graphic dinamis\n"
                "• Sinkronisasi audio & visual\n"
                "• Revisi hingga 2x\n"
                "• Format MP4\n"
                "💰 *Harga: Rp 95.000*\n\n"

                "*Tingkat Kesulitan 5*\n"
                "• Konsep kreatif & storytelling penuh\n"
                "• Durasi 5–10 menit\n"
                "• Motion graphic kompleks\n"
                "• Sinkronisasi audio profesional\n"
                "• Revisi hingga 3x\n"
                "• Format MP4\n"
                "💰 *Harga: Rp 99.999*\n\n"

                "Jika ingin melanjutkan pemesanan,\n"
                "silakan hubungi admin 😊"
            ),
            parse_mode="Markdown",
            reply_markup=order_button(
                "order_company_profile_animation",
                "main"
            ),
        )
        return

    # ------------ MENU PRODUCT EXPLAINER VIDEO ------------
    if data == "menu_product_explainer_video":
        context.user_data["selected_service"] = "Product Explainer Video"
        query.edit_message_text(
            text=(
                "🖼 *Product Explainer Video*\n\n"
                "Detail Layanan:\n\n"

                "*Tingkat Kesulitan 1*\n"
                "• Penjelasan produk berbasis teks & gambar\n"
                "• Durasi ±1 menit\n"
                "• Transisi sederhana\n"
                "• Revisi hingga 1x\n"
                "• Format MP4\n"
                "💰 *Harga: Rp 70.000*\n\n"

                "*Tingkat Kesulitan 2*\n"
                "• Penjelasan produk dengan ikon visual\n"
                "• Durasi 1–2 menit\n"
                "• Animasi ringan\n"
                "• Revisi hingga 1x\n"
                "• Format MP4\n"
                "💰 *Harga: Rp 80.000*\n\n"

                "*Tingkat Kesulitan 3*\n"
                "• Alur cerita produk terstruktur\n"
                "• Durasi 2–3 menit\n"
                "• Animasi ikon & teks dinamis\n"
                "• Background music\n"
                "• Revisi hingga 2x\n"
                "• Format MP4\n"
                "💰 *Harga: Rp 90.000*\n\n"

                "*Tingkat Kesulitan 4*\n"
                "• Storytelling produk lengkap\n"
                "• Durasi 3–5 menit\n"
                "• Motion graphic menengah\n"
                "• Sinkronisasi audio & visual\n"
                "• Revisi hingga 2x\n"
                "• Format MP4\n"
                "💰 *Harga: Rp 95.000*\n\n"

                "*Tingkat Kesulitan 5*\n"
                "• Konsep kreatif & narasi penuh\n"
                "• Durasi 5–10 menit\n"
                "• Motion graphic kompleks\n"
                "• Sinkronisasi audio profesional\n"
                "• Revisi hingga 3x\n"
                "• Format MP4\n"
                "💰 *Harga: Rp 99.999*\n\n"

                "Jika ingin melanjutkan pemesanan,\n"
                "silakan hubungi admin 😊"
            ),
            parse_mode="Markdown",
            reply_markup=order_button(
                "order_product_explainer_video",
                "main"
            ),
        )
        return

    # ------------ MENU ANIMATION ------------
    if data == "menu_animation":
        context.user_data["selected_service"] = "Animation"
        query.edit_message_text(
            text=(
                "🎞 *Animation*\n\n"
                "Detail Layanan:\n\n"

                "*Tingkat Kesulitan 1*\n"
                "• Animasi teks sederhana\n"
                "• Durasi ±1 menit\n"
                "• Transisi dasar\n"
                "• Revisi hingga 1x\n"
                "• Format MP4\n"
                "💰 *Harga: Rp 70.000*\n\n"

                "*Tingkat Kesulitan 2*\n"
                "• Animasi ikon & teks sederhana\n"
                "• Durasi 1–2 menit\n"
                "• Movement ringan\n"
                "• Revisi hingga 1x\n"
                "• Format MP4\n"
                "💰 *Harga: Rp 80.000*\n\n"

                "*Tingkat Kesulitan 3*\n"
                "• Animasi visual terstruktur\n"
                "• Durasi 2–3 menit\n"
                "• Movement menengah\n"
                "• Sinkronisasi visual\n"
                "• Revisi hingga 2x\n"
                "• Format MP4\n"
                "💰 *Harga: Rp 90.000*\n\n"

                "*Tingkat Kesulitan 4*\n"
                "• Storytelling animasi\n"
                "• Durasi 3–5 menit\n"
                "• Movement dinamis\n"
                "• Transisi kompleks\n"
                "• Revisi hingga 2x\n"
                "• Format MP4\n"
                "💰 *Harga: Rp 95.000*\n\n"

                "*Tingkat Kesulitan 5*\n"
                "• Konsep animasi penuh\n"
                "• Durasi 5–10 menit\n"
                "• Movement kompleks & detail\n"
                "• Sinkronisasi audio & visual\n"
                "• Revisi hingga 3x\n"
                "• Format MP4\n"
                "💰 *Harga: Rp 99.999*\n\n"

                "Jika ingin melanjutkan pemesanan,\n"
                "silakan hubungi admin 😊"
            ),
            parse_mode="Markdown",
            reply_markup=order_button(
                "order_animation",
                "main"
            ),
        )
        return

    # ------------ MENU OVERLAY STREAM ------------
    if data == "menu_overlay_stream":
        context.user_data["selected_service"] = "Overlay Stream"
        query.edit_message_text(
            text=(
                "🎞 *Animation*\n\n"
                "💼 *Overlay Stream*\n\n"
                "Detail Layanan:\n\n"

                "*Tingkat Kesulitan 1*\n"
                "• Overlay layar sederhana\n"
                "• Webcam frame basic\n"
                "• Tanpa animasi\n"
                "• Revisi hingga 1x\n"
                "• File PNG\n"
                "💰 *Harga: Rp 70.000*\n\n"

                "*Tingkat Kesulitan 2*\n"
                "• Overlay layar + webcam frame\n"
                "• Animasi ringan (fade / slide)\n"
                "• Alert basic\n"
                "• Revisi hingga 1x\n"
                "• File PNG\n"
                "💰 *Harga: Rp 80.000*\n\n"

                "*Tingkat Kesulitan 3*\n"
                "• Overlay lengkap (screen, webcam, alert)\n"
                "• Animasi transisi menengah\n"
                "• Desain konsisten\n"
                "• Revisi hingga 2x\n"
                "• File PNG + PSD\n"
                "💰 *Harga: Rp 90.000*\n\n"

                "*Tingkat Kesulitan 4*\n"
                "• Overlay profesional\n"
                "• Animasi dinamis\n"
                "• Alert interaktif\n"
                "• Branding warna & font\n"
                "• Revisi hingga 2x\n"
                "• File PNG + PSD\n"
                "💰 *Harga: Rp 95.000*\n\n"

                "*Tingkat Kesulitan 5*\n"
                "• Overlay custom premium\n"
                "• Animasi kompleks & detail\n"
                "• Alert full motion\n"
                "• Konsep visual eksklusif\n"
                "• Revisi hingga 3x\n"
                "• File PNG + PSD\n"
                "💰 *Harga: Rp 99.999*\n\n"

                "Jika ingin melanjutkan pemesanan,\n"
                "silakan hubungi admin 😊"
            ),
            parse_mode="Markdown",
            reply_markup=order_button(
                "order_overlay_stream",
                "main"
            ),
        )
        return

    # ------------ MENU MUSIC VIDEO ------------
    if data == "menu_music_video":
        context.user_data["selected_service"] = "Music Video"
        query.edit_message_text(
            text=(
                "🎵 *Music Video*\n\n"
                "Detail Layanan:\n\n"

                "*Tingkat Kesulitan 1*\n"
                "• Visual statis + teks judul\n"
                "• Durasi ±1 menit\n"
                "• Tanpa animasi kompleks\n"
                "• Revisi hingga 1x\n"
                "• Format MP4\n"
                "💰 *Harga: Rp 70.000*\n\n"

                "*Tingkat Kesulitan 2*\n"
                "• Visual sederhana + beat cut ringan\n"
                "• Durasi 1–2 menit\n"
                "• Movement dasar\n"
                "• Revisi hingga 1x\n"
                "• Format MP4\n"
                "💰 *Harga: Rp 80.000*\n\n"

                "*Tingkat Kesulitan 3*\n"
                "• Sinkronisasi visual dengan beat musik\n"
                "• Durasi 2–3 menit\n"
                "• Movement menengah\n"
                "• Transisi dinamis\n"
                "• Revisi hingga 2x\n"
                "• Format MP4\n"
                "💰 *Harga: Rp 90.000*\n\n"

                "*Tingkat Kesulitan 4*\n"
                "• Visual storytelling\n"
                "• Durasi 3–5 menit\n"
                "• Movement dinamis\n"
                "• Sinkronisasi audio & visual\n"
                "• Revisi hingga 2x\n"
                "• Format MP4\n"
                "💰 *Harga: Rp 95.000*\n\n"

                "*Tingkat Kesulitan 5*\n"
                "• Konsep music video penuh\n"
                "• Durasi 5–10 menit\n"
                "• Movement kompleks & detail\n"
                "• Editing profesional sesuai beat\n"
                "• Revisi hingga 3x\n"
                "• Format MP4\n"
                "💰 *Harga: Rp 99.999*\n\n"

                "Jika ingin melanjutkan pemesanan,\n"
                "silakan hubungi admin 😊"
            ),
            parse_mode="Markdown",
            reply_markup=order_button(
                "order_music_video",
                "main"
            ),
        )
        return

    # ------------ HUBUNGI ADMIN TANPA ORDER ------------
    if data == "contact_admin_general":
        context.user_data["stage"] = "CHAT_ADMIN"
        context.user_data["admin_mode"] = True
        context.user_data["active_invoice_id"] = None

        query.edit_message_text(
            "Baik, Arcade Buddy! 😊\n"
            "Kamu sekarang terhubung ke admin.\n"
            "Silakan ketik pertanyaan atau jelaskan kebutuhan desainmu.",
        )

        send_text_to_admin(
            user, "User ingin dihubungkan ke admin (tanpa memilih paket spesifik).")
        return

    # ------------ ORDER CALLBACK ------------
    if data.startswith("contact_admin|"):
        order_key = data.split("|", 1)[1]
        svc = ORDER_CATALOG.get(order_key)

        # SIMPAN DATA SAJA (BELUM ORDER)
        context.user_data["admin_mode"] = True
        context.user_data["stage"] = "CHAT_ADMIN"
        context.user_data["service_label"] = svc["label"]
        context.user_data["unit_price"] = svc["price"]

        service = context.user_data.get("selected_service", "layanan")

        query.edit_message_text(
            f"✅ Kamu sudah terhubung dengan Admin.\n"
            f"Silakan jelaskan kebutuhan *{service}* kamu ya 😊",
            parse_mode="Markdown"
        )
        return

# ==============================
# USER MESSAGE HANDLER
# ==============================

def user_message(update: Update, context: CallbackContext):
    user = update.effective_user
    msg = update.message
    ud = context.user_data
    stage = ud.get("stage")

    # =======================
    # /start RESET
    # =======================
    if msg.text and msg.text.lower() == "/start":
        ud.clear()
        send_banner(update, context)
        msg.reply_text(
            "Silakan pilih layanan yang ingin dipesan ✨",
            parse_mode="Markdown",
            reply_markup=main_menu(),
        )
        return

    # =======================
    # CEK BUKTI PEMBAYARAN (HARUS PALING ATAS)
    # =======================
    if stage == "WAIT_PAYMENT":
        if msg.photo or msg.document:
            forward_media_to_admin(update, context)
            ud["stage"] = "WAIT_ADMIN_CONFIRM"
            msg.reply_text(
                "Terima kasih.\n"
                "Bukti pembayaran sudah dikirim ke admin.\n"
                "Pesanan Anda akan kami kirim paling lambat H+5 dari sekarang 😊"
            )
            return
        else:
            msg.reply_text(
                "Silakan kirim *bukti pembayaran berupa foto atau file* 🙏",
                parse_mode="Markdown"
            )
            return

    # =======================
    # MODE CHAT ADMIN
    # =======================
    if ud.get("admin_mode") and stage == "CHAT_ADMIN":

        # hanya teks
        if not msg.text:
            msg.reply_text("Silakan kirim pesan teks ya 😊")
            return

        text = msg.text.lower().strip()

        # trigger tingkat kesulitan
        import re
        LEVEL_MAP = {
            "1": 70000,
            "2": 80000,
            "3": 90000,
            "4": 95000,
            "5": 99999,
        }

        match = re.search(r"tingkat\s+kesulitan\s+([1-5])", text)
        if match:
            lvl = match.group(1)
            ud["level"] = f"Tingkat Kesulitan {lvl}"
            ud["unit_price"] = LEVEL_MAP[lvl]
            ud["stage"] = "ASK_QTY"

            msg.reply_text(
                f"✅ *Pilihan diterima*\n\n"
                f"Layanan : *{ud['service_label']}*\n"
                f"Tingkat : *{ud['level']}*\n"
                f"Harga   : *Rp {ud['unit_price']:,} / item*\n\n"
                "Masukkan *jumlah (quantity)* yang ingin dipesan, Contoh: 2",
                parse_mode="Markdown"
            )
            return

        # forward chat ke admin
        send_text_to_admin(user, msg.text)
        return

    # =======================
    # ORDER HARUS TEKS
    # =======================
    if not msg.text:
        msg.reply_text("Untuk proses order, kirimkan pesan teks ya 😊")
        return

    text = msg.text.strip().lower()

    # =======================
    # INPUT QTY
    # =======================
    if stage == "ASK_QTY":
        if not text.isdigit() or int(text) <= 0:
            msg.reply_text("Masukkan quantity yang valid. Contoh: 2")
            return

        ud["qty"] = int(text)
        ud["stage"] = "CONFIRM_ORDER"

        total = ud["unit_price"] * ud["qty"]
        msg.reply_text(
            "🧾 *Rangkuman Order*\n\n"
            f"Layanan : *{ud['service_label']}*\n"
            f"Tingkat : *{ud['level']}*\n"
            f"Qty     : *{ud['qty']}*\n"
            f"Total   : *Rp {total:,}*\n\n"
            "Ketik *ya* untuk order atau *batal*.",
            parse_mode="Markdown"
        )
        return

    # =======================
    # KONFIRMASI ORDER
    # =======================
    if stage == "CONFIRM_ORDER":

        if text == "batal":
            ud.clear()
            msg.reply_text("Order dibatalkan. Ketik /start untuk order lagi 😊")
            return

        if text == "ya":
            invoice = create_invoice(
                user,
                ud["service_label"],
                ud["unit_price"],
                ud["qty"]
            )

            ud["stage"] = "WAIT_PAYMENT"
            ud["active_invoice_id"] = invoice["invoice_id"]

            msg.reply_text(
                f"🧾 *Invoice {invoice['invoice_id']}*\n\n"
                f"Layanan : *{invoice['service_label']}*\n"
                f"Tingkat : *{ud['level']}*\n"
                f"Qty     : *{invoice['qty']}*\n"
                f"Total   : *Rp {invoice['total_price']:,}*\n\n"
                f"{PAYMENT_TEXT}\n"
                "Silakan kirim *bukti pembayaran* 🙏",
                parse_mode="Markdown"
            )

            notify_new_order_to_admin(user, invoice)
            return

    # =======================
    # TERIMA HASIL DARI ADMIN
    # =======================
    if stage == "WAIT_ADMIN_CONFIRM":

        # Admin kirim LINK (figma / drive)
        if msg.text and msg.text.startswith("http"):
            msg.reply_text(
                "🎉 *Hasil Pesanan Kamu Sudah Siap!*\n\n"
                f"🔗 {msg.text}\n\n"
                "Silakan dicek ya 😊\n"
                "Ketik *puas* jika sudah sesuai atau *revisi* jika perlu perbaikan.",
                parse_mode="Markdown"
            )
            return

        # Admin kirim FILE (png / mp4 / pdf)
        if msg.photo or msg.document or msg.video:
            msg.reply_text(
                "🎉 *Hasil Pesanan Kamu Sudah Siap!*\n\n"
                "Silakan dicek hasilnya 😊\n"
                "Ketik *puas* jika sudah sesuai atau *revisi* jika perlu perbaikan.",
                parse_mode="Markdown"
            )
            return

    # =======================
    # FEEDBACK CUSTOMER
    # =======================
    if stage == "WAIT_ADMIN_CONFIRM" and msg.text:
        text = msg.text.lower().strip()

        if text == "puas":
            invoice_id = ud.get("active_invoice_id")
            invoices = load_invoices()

            for inv in invoices:
                if inv["invoice_id"] == invoice_id:
                    inv["status"] = "COMPLETED"
                    break

            save_invoices(invoices)

            ud["order_completed"] = True
            ud.clear()

            msg.reply_text(
                "🎉 *Terima kasih sudah menggunakan Arcade Studio!* 🎨✨\n\n"
                "Pesanan kamu telah *selesai* ✅\n"
                "Ketik /start untuk melakukan pemesanan berikutnya 😊",
                parse_mode="Markdown"
            )
            return


        # CUSTOMER MINTA REVISI
        if text == "revisi":
            ud["stage"] = "CHAT_ADMIN"
            msg.reply_text(
                "Baik 😊\n"
                "Silakan jelaskan revisi yang kamu inginkan, nanti akan kami sampaikan ke admin.",
                parse_mode="Markdown"
            )
            return



# ==============================
# MAIN
# ==============================

def main():
    updater = Updater(CUSTOMER_BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(button_handler))
    # Satu handler untuk semua pesan private (teks + foto + dokumen)
    dp.add_handler(MessageHandler(Filters.private &
                   ~Filters.command, user_message))

    print("Customer Bot berjalan…")
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
