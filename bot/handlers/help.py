# bot/handlers/help.py

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton

async def help_command(update: Update, context):
    telegraph_url = "https://telegra.ph/Selamat-Datang-di-EVM-Lens-Bot-Beta-07-24" 
    
    text = (
        "❓ **Bantuan EVM Lens Bot**\n\n"
        "Gunakan menu di bawah /start untuk mengakses semua fitur:\n\n"
        "🔹 **Tambah/Hapus Wallet:** Kelola daftar pantauan Anda.\n"
        "🔹 **Cek Portfolio:** Lihat daftar Token & NFT.\n"
        "🔹 **Pengaturan Notifikasi:** Atur preferensi notifikasi.\n"
        "🔹 **Cek Gas Fee:** Periksa biaya transaksi.\n\n"
        "Info lebih detail, roadmap, dan kontak author ada di halaman informasi kami."
    )
    
    keyboard = [[InlineKeyboardButton("📖 Baca Info Lengkap & Roadmap", url=telegraph_url)]]
    
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')