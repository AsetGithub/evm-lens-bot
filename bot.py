import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Impor dari file kita sendiri
import config
import database

# Setup logging untuk melihat aktivitas bot di terminal
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Fungsi untuk perintah /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_html(
        f"Halo {user.mention_html()}!\n\n"
        "Saya adalah EVM Lens Bot. Saya bisa membantumu memantau wallet.\n\n"
        "Gunakan /add_wallet <chain> <address> untuk memulai."
    )

# Fungsi untuk perintah /add_wallet
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # Ambil argumen setelah perintah, contoh: polygon 0x123...
    args = context.args
    if len(args) != 2:
        await update.message.reply_text("Format salah. Gunakan: /add_wallet <chain> <address>")
        return

    chain, address = args[0], args[1]

    # Panggil fungsi dari database.py
    success = database.add_wallet(user_id, address, chain)

    if success:
        await update.message.reply_text(f"✅ Wallet {address} di jaringan {chain} berhasil ditambahkan!")
    else:
        await update.message.reply_text(f"ℹ️ Wallet {address} sudah ada di daftar pantauan Anda.")

def main():
    """Fungsi utama untuk menjalankan bot."""
    # Pertama, siapkan database
    database.setup_database()

    # Buat aplikasi bot
    application = Application.builder().token(config.TELEGRAM_TOKEN).build()

    # Daftarkan semua perintah
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add_wallet", add))
    # (Perintah lain seperti /remove_wallet akan kita tambahkan nanti)

    print("Bot sedang berjalan...")
    # Jalankan bot sampai dihentikan (Ctrl+C)
    application.run_polling()

if __name__ == '__main__':
    main()