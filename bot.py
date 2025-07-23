import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler,
    filters, ConversationHandler
)

# Impor dari file kita sendiri
import config
import database
from monitor import CHAIN_CONFIG # Kita impor konfigurasi jaringan

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Definisikan state untuk alur percakapan
GET_ADDRESS, SELECT_CHAIN = range(2)

# --- Fungsi Menu & Tombol ---

def get_main_menu_keyboard():
    """Membuat keyboard untuk menu utama."""
    keyboard = [[InlineKeyboardButton("➕ Tambah Wallet untuk Dipantau", callback_data='add_wallet_start')]]
    return InlineKeyboardMarkup(keyboard)

def get_network_keyboard():
    """Membuat keyboard pilihan jaringan secara dinamis dari CHAIN_CONFIG."""
    keyboard = []
    # Membuat 3 tombol per baris
    row = []
    for chain in CHAIN_CONFIG.keys():
        row.append(InlineKeyboardButton(chain.title(), callback_data=f"chain_{chain}"))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("❌ Batalkan", callback_data='cancel')])
    return InlineKeyboardMarkup(keyboard)

# --- Fungsi Handler Utama ---

async def start(update: Update, context):
    """Mengirim pesan selamat datang dengan menu utama."""
    user = update.effective_user
    text = f"Halo {user.mention_html()}!\n\nSaya EVM Lens Bot, siap membantumu. Pilih menu di bawah untuk memulai."
    
    # Menangani jika ini adalah callback dari tombol
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(text=text, reply_markup=get_main_menu_keyboard(), parse_mode='HTML')
    else:
        await update.message.reply_html(text, reply_markup=get_main_menu_keyboard())
    
    # Pastikan percakapan sebelumnya selesai
    return ConversationHandler.END

# --- Alur Percakapan Tambah Wallet ---

async def add_wallet_start(update: Update, context):
    """Langkah 1: Memulai alur, meminta alamat wallet."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="Oke, silakan kirim alamat wallet (contoh: 0x...) yang ingin Anda pantau.")
    return GET_ADDRESS

async def get_address(update: Update, context):
    """Langkah 2: Menerima alamat, menyimpan sementara, dan meminta pilih jaringan."""
    address = update.message.text
    # Simpan alamat di data pengguna sementara
    context.user_data['wallet_address_to_add'] = address
    
    await update.message.reply_text(
        f"Alamat diterima! Sekarang pilih satu jaringan untuk memantau <code>{address}</code>:",
        reply_markup=get_network_keyboard(),
        parse_mode='HTML'
    )
    return SELECT_CHAIN

async def select_chain(update: Update, context):
    """Langkah 3: Menerima pilihan jaringan, menyimpan ke DB, dan mengakhiri."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    address = context.user_data.get('wallet_address_to_add')
    chain = query.data.split('_')[1] # Ambil nama chain dari callback_data 'chain_polygon'

    if not address:
        await query.edit_message_text(
            "Terjadi kesalahan, alamat tidak ditemukan. Silakan mulai lagi.",
            reply_markup=get_main_menu_keyboard()
        )
        return ConversationHandler.END

    success = database.add_wallet(user_id, address, chain)
    if success:
        await query.edit_message_text(f"✅ Berhasil! Wallet <code>{address}</code> sekarang dipantau di jaringan {chain.title()}.", parse_mode='HTML')
    else:
        await query.edit_message_text(f"ℹ️ Wallet <code>{address}</code> sudah ada di daftar pantauan Anda untuk jaringan {chain.title()}.", parse_mode='HTML')

    # Tampilkan kembali menu utama setelah selesai
    # Kita panggil fungsi start lagi dengan cara yang sedikit berbeda
    await start(update, context)
    
    return ConversationHandler.END

async def cancel(update: Update, context):
    """Membatalkan alur percakapan."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Proses penambahan wallet dibatalkan.", reply_markup=get_main_menu_keyboard())
    return ConversationHandler.END

# --- Main ---
def main():
    """Fungsi utama untuk menjalankan bot."""
    database.setup_database()
    application = Application.builder().token(config.TELEGRAM_TOKEN).build()

    # Conversation handler untuk proses tambah wallet yang interaktif
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_wallet_start, pattern='^add_wallet_start$')],
        states={
            GET_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_address)],
            SELECT_CHAIN: [CallbackQueryHandler(select_chain, pattern='^chain_')],
        },
        fallbacks=[CallbackQueryHandler(cancel, pattern='^cancel$'), CommandHandler('start', start)]
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    
    print("Bot berjalan dengan menu interaktif multi-jaringan...")
    application.run_polling()

if __name__ == '__main__':
    main()
