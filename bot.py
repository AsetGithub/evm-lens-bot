import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler,
    filters, ConversationHandler
)

import config
import database
from monitor import CHAIN_CONFIG

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Definisikan state untuk alur percakapan
GET_ADDRESS, SELECT_CHAIN = range(2)

# --- Fungsi Menu & Tombol ---

def get_main_menu_keyboard():
    """Membuat keyboard untuk menu utama."""
    keyboard = [
        [InlineKeyboardButton("➕ Tambah Wallet", callback_data='add_wallet_start')],
        [
            InlineKeyboardButton("📂 Wallet Saya", callback_data='my_wallets'),
            InlineKeyboardButton("🗑️ Hapus Wallet", callback_data='remove_wallet_menu')
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_network_keyboard():
    """Membuat keyboard pilihan jaringan secara dinamis."""
    keyboard = [[InlineKeyboardButton(chain.title(), callback_data=f"chain_{chain}")] for chain in CHAIN_CONFIG.keys()]
    keyboard.append([InlineKeyboardButton("❌ Batalkan", callback_data='cancel')])
    return InlineKeyboardMarkup(keyboard)

# --- Fungsi Handler Utama ---

async def start(update: Update, context):
    """Mengirim pesan selamat datang dengan menu utama."""
    user = update.effective_user
    text = f"Halo {user.mention_html()}!\n\nSaya EVM Lens Bot, siap membantumu. Pilih menu di bawah."
    
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(text=text, reply_markup=get_main_menu_keyboard(), parse_mode='HTML')
    else:
        await update.message.reply_html(text, reply_markup=get_main_menu_keyboard())
    
    return ConversationHandler.END

# --- Alur Tampilkan & Hapus Wallet ---

async def my_wallets(update: Update, context):
    """Menampilkan daftar wallet yang dipantau pengguna."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    wallets = database.get_wallets_by_user(user_id)
    
    if not wallets:
        text = "Anda belum menambahkan wallet apapun untuk dipantau."
    else:
        text = "Berikut adalah daftar wallet yang Anda pantau:\n\n"
        for _, address, chain in wallets:
            text += f"🔹 <b>{chain.title()}</b>: <code>{address}</code>\n"
            
    keyboard = [[InlineKeyboardButton("⬅️ Kembali ke Menu Utama", callback_data='main_menu')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def remove_wallet_menu(update: Update, context):
    """Menampilkan daftar wallet dengan tombol hapus di sebelahnya."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    wallets = database.get_wallets_by_user(user_id)
    
    if not wallets:
        await query.edit_message_text(
            "Anda tidak memiliki wallet untuk dihapus.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Kembali", callback_data='main_menu')]])
        )
        return

    keyboard = []
    for wallet_id, address, chain in wallets:
        # Callback data berisi 'delete_{id_wallet}'
        button_text = f"❌ Hapus {chain.title()}: {address[:6]}...{address[-4:]}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"delete_{wallet_id}")])
    
    keyboard.append([InlineKeyboardButton("⬅️ Kembali", callback_data='main_menu')])
    await query.edit_message_text("Pilih wallet yang ingin Anda hapus:", reply_markup=InlineKeyboardMarkup(keyboard))

async def remove_wallet_confirm(update: Update, context):
    """Menghapus wallet dari database setelah tombol konfirmasi ditekan."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    wallet_id_to_delete = int(query.data.split('_')[1])
    
    success = database.remove_wallet_by_id(wallet_id_to_delete, user_id)
    
    if success:
        await query.edit_message_text("✅ Wallet berhasil dihapus dari daftar pantauan.")
    else:
        await query.edit_message_text("❌ Gagal menghapus wallet. Mungkin sudah dihapus sebelumnya.")
        
    # Tampilkan kembali menu utama
    await start(update, context)

# --- Alur Percakapan Tambah Wallet (Sama seperti sebelumnya) ---

async def add_wallet_start(update: Update, context):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="Oke, silakan kirim alamat wallet (contoh: 0x...) yang ingin Anda pantau.")
    return GET_ADDRESS

async def get_address(update: Update, context):
    address = update.message.text
    context.user_data['wallet_address_to_add'] = address
    await update.message.reply_text(
        f"Alamat diterima! Sekarang pilih satu jaringan untuk memantau <code>{address}</code>:",
        reply_markup=get_network_keyboard(), parse_mode='HTML'
    )
    return SELECT_CHAIN

async def select_chain(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    address = context.user_data.get('wallet_address_to_add')
    chain = query.data.split('_')[1]
    if not address:
        await query.edit_message_text("Terjadi kesalahan, silakan mulai lagi.", reply_markup=get_main_menu_keyboard())
        return ConversationHandler.END
    success = database.add_wallet(user_id, address, chain)
    if success:
        await query.edit_message_text(f"✅ Berhasil! Wallet <code>{address}</code> sekarang dipantau di jaringan {chain.title()}.", parse_mode='HTML')
    else:
        await query.edit_message_text(f"ℹ️ Wallet <code>{address}</code> sudah ada di daftar pantauan Anda untuk jaringan {chain.title()}.", parse_mode='HTML')
    await start(update, context)
    return ConversationHandler.END

async def cancel(update: Update, context):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Proses dibatalkan.", reply_markup=get_main_menu_keyboard())
    return ConversationHandler.END

# --- Main ---
def main():
    database.setup_database()
    application = Application.builder().token(config.TELEGRAM_TOKEN).build()

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
    
    # Handler untuk tombol-tombol baru
    application.add_handler(CallbackQueryHandler(my_wallets, pattern='^my_wallets$'))
    application.add_handler(CallbackQueryHandler(remove_wallet_menu, pattern='^remove_wallet_menu$'))
    application.add_handler(CallbackQueryHandler(remove_wallet_confirm, pattern='^delete_'))
    application.add_handler(CallbackQueryHandler(start, pattern='^main_menu$'))
    
    print("Bot berjalan dengan fitur manajemen wallet lengkap...")
    application.run_polling()

if __name__ == '__main__':
    main()
