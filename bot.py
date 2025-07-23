import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler

# Impor dari file kita sendiri
import config
import database

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Definisikan state untuk ConversationHandler
CHAIN, ADDRESS = range(2)

# Fungsi untuk membuat menu utama
def get_main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("➕ Tambah Wallet", callback_data='add_wallet')],
        # Tombol lain akan kita tambahkan di sini nanti
        # [InlineKeyboardButton("📂 Wallet Saya", callback_data='my_wallets')],
        # [InlineKeyboardButton("🗑️ Hapus Wallet", callback_data='remove_wallet')],
    ]
    return InlineKeyboardMarkup(keyboard)

# Fungsi untuk perintah /start dan tombol kembali
async def start(update: Update, context):
    user = update.effective_user
    text = f"Halo {user.mention_html()}!\n\nSaya EVM Lens Bot, siap membantumu memantau wallet. Silakan pilih menu di bawah."
    
    # Jika dari callback query (tombol), edit pesan. Jika dari command, kirim pesan baru.
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(text=text, reply_markup=get_main_menu_keyboard(), parse_mode='HTML')
    else:
        await update.message.reply_html(text, reply_markup=get_main_menu_keyboard())
    
    return -1 # Akhiri percakapan jika ada

# Fungsi yang dipanggil saat tombol 'add_wallet' ditekan
async def add_wallet_start(update: Update, context):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="Silakan masukkan nama jaringan (misalnya: polygon, bsc, ethereum):")
    return CHAIN

# Fungsi untuk menerima nama jaringan
async def received_chain(update: Update, context):
    context.user_data['chain'] = update.message.text.lower()
    await update.message.reply_text(f"Jaringan '{context.user_data['chain']}' diterima. Sekarang, silakan masukkan alamat wallet:")
    return ADDRESS

# Fungsi untuk menerima alamat dan menyimpan ke DB
async def received_address(update: Update, context):
    user_id = update.effective_user.id
    address = update.message.text
    chain = context.user_data['chain']

    success = database.add_wallet(user_id, address, chain)
    if success:
        await update.message.reply_text(f"✅ Wallet {address} di jaringan {chain} berhasil ditambahkan!")
    else:
        await update.message.reply_text(f"ℹ️ Wallet {address} sudah ada di daftar pantauan Anda.")
    
    # Tampilkan menu utama lagi
    await start(update, context)
    return -1 # Akhiri percakapan

# Fungsi untuk membatalkan proses
async def cancel(update: Update, context):
    await update.message.reply_text("Proses dibatalkan.")
    await start(update, context)
    return -1

def main():
    database.setup_database()
    application = Application.builder().token(config.TELEGRAM_TOKEN).build()

    # Conversation handler untuk proses tambah wallet
    add_wallet_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_wallet_start, pattern='^add_wallet$')],
        states={
            CHAIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_chain)],
            ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_address)],
        },
        fallbacks=[CommandHandler('start', start)]
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(add_wallet_conv)
    # Handler untuk tombol kembali ke menu utama dari state lain (jika ada)
    application.add_handler(CallbackQueryHandler(start, pattern='^main_menu$'))

    print("Bot sedang berjalan dengan fitur interaktif...")
    application.run_polling()

if __name__ == '__main__':
    main()