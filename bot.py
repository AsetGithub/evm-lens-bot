# bot.py (Versi dengan Fitur Portfolio)

import logging
import requests
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

# --- Fungsi RPC Helper (Baru) ---
def make_rpc_request(rpc_url, method, params):
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    try:
        response = requests.post(rpc_url, json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logging.error(f"Error saat melakukan request ke RPC: {e}")
    return None

# --- Fungsi Menu & Tombol ---

def get_main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("➕ Tambah Wallet", callback_data='add_wallet_start')],
        [
            InlineKeyboardButton("📂 Wallet Saya", callback_data='my_wallets'),
            InlineKeyboardButton("🗑️ Hapus Wallet", callback_data='remove_wallet_menu')
        ],
        [InlineKeyboardButton("📊 Cek Portfolio", callback_data='portfolio_start')]
    ]
    return InlineKeyboardMarkup(keyboard)

# (Fungsi get_network_keyboard tetap sama)
def get_network_keyboard():
    keyboard = []
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
    user = update.effective_user
    text = f"Halo {user.mention_html()}!\n\nSaya EVM Lens Bot, siap membantumu. Pilih menu di bawah."
    
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(text=text, reply_markup=get_main_menu_keyboard(), parse_mode='HTML')
    else:
        await update.message.reply_html(text, reply_markup=get_main_menu_keyboard())
    
    return ConversationHandler.END

# --- Alur Tampilkan & Hapus Wallet (Tetap sama) ---
async def my_wallets(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    wallets = database.get_wallets_by_user(user_id)
    if not wallets:
        text = "Anda belum menambahkan wallet apapun."
    else:
        text = "Berikut adalah daftar wallet yang Anda pantau:\n\n"
        for _, address, chain in wallets:
            text += f"🔹 <b>{chain.title()}</b>: <code>{address}</code>\n"
    keyboard = [[InlineKeyboardButton("⬅️ Kembali", callback_data='main_menu')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def remove_wallet_menu(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    wallets = database.get_wallets_by_user(user_id)
    if not wallets:
        await query.edit_message_text("Anda tidak memiliki wallet untuk dihapus.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Kembali", callback_data='main_menu')]]))
        return
    keyboard = []
    for wallet_id, address, chain in wallets:
        button_text = f"❌ Hapus {chain.title()}: {address[:6]}...{address[-4:]}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"delete_{wallet_id}")])
    keyboard.append([InlineKeyboardButton("⬅️ Kembali", callback_data='main_menu')])
    await query.edit_message_text("Pilih wallet yang ingin Anda hapus:", reply_markup=InlineKeyboardMarkup(keyboard))

async def remove_wallet_confirm(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    wallet_id_to_delete = int(query.data.split('_')[1])
    success = database.remove_wallet_by_id(wallet_id_to_delete, user_id)
    if success:
        await query.edit_message_text("✅ Wallet berhasil dihapus.")
    else:
        await query.edit_message_text("❌ Gagal menghapus wallet.")
    await start(update, context)

# --- Alur Tambah Wallet (Tetap sama) ---
async def add_wallet_start(update: Update, context):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="Oke, kirim alamat wallet (contoh: 0x...) yang ingin Anda pantau.")
    return GET_ADDRESS

async def get_address(update: Update, context):
    address = update.message.text
    context.user_data['wallet_address_to_add'] = address
    await update.message.reply_text(f"Alamat diterima! Sekarang pilih jaringan untuk memantau <code>{address}</code>:", reply_markup=get_network_keyboard(), parse_mode='HTML')
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

# --- Alur Portfolio (BARU) ---
async def portfolio_start(update: Update, context):
    """Langkah 1 Portfolio: Menampilkan daftar wallet untuk dipilih."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    wallets = database.get_wallets_by_user(user_id)
    if not wallets:
        await query.edit_message_text("Anda belum memiliki wallet untuk dilihat portfolionya.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Kembali", callback_data='main_menu')]]))
        return
    
    keyboard = []
    for wallet_id, address, chain in wallets:
        button_text = f"{chain.title()}: {address[:6]}...{address[-4:]}"
        # Callback data berisi 'portfolio_{chain}_{address}'
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"portfolio_{chain}_{address}")])
    
    keyboard.append([InlineKeyboardButton("⬅️ Kembali", callback_data='main_menu')])
    await query.edit_message_text("Pilih wallet yang ingin Anda lihat portfolionya:", reply_markup=InlineKeyboardMarkup(keyboard))

async def get_portfolio(update: Update, context):
    """Langkah 2 Portfolio: Mengambil data dan menampilkannya."""
    query = update.callback_query
    await query.answer()
    
    # Tampilkan pesan loading
    await query.edit_message_text("⏳ Sedang mengambil data portfolio, mohon tunggu...")

    _, chain, address = query.data.split('_')
    
    rpc_url = f"https://{CHAIN_CONFIG[chain]['rpc_subdomain']}.g.alchemy.com/v2/{config.ALCHEMY_API_KEY}"
    
    # Ambil saldo token ERC-20
    params = [address, "erc20"]
    response = make_rpc_request(rpc_url, "alchemy_getTokenBalances", params)
    
    text = f"<b>📊 Portfolio untuk <code>{address}</code> di jaringan {chain.title()}</b>\n\n"
    
    if response and 'result' in response and response['result'].get('tokenBalances'):
        token_balances = response['result']['tokenBalances']
        for token in token_balances:
            balance_hex = token.get('tokenBalance', '0x0')
            if balance_hex and int(balance_hex, 16) > 0:
                # Ambil metadata token
                metadata_response = make_rpc_request(rpc_url, "alchemy_getTokenMetadata", [token['contractAddress']])
                if metadata_response and 'result' in metadata_response:
                    metadata = metadata_response['result']
                    symbol = metadata.get('symbol', 'UNKNOWN')
                    decimals = metadata.get('decimals', 18)
                    balance = int(balance_hex, 16) / (10 ** decimals)
                    if balance > 0.000001: # Filter debu
                        text += f"<b>- {balance:,.6f} {symbol}</b>\n"
    else:
        text += "Tidak ada token ERC-20 yang ditemukan.\n"
        
    keyboard = [[InlineKeyboardButton("⬅️ Kembali ke Menu", callback_data='main_menu')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

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
        fallbacks=[CallbackQueryHandler(start, pattern='^main_menu$'), CommandHandler('start', start)]
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    
    application.add_handler(CallbackQueryHandler(my_wallets, pattern='^my_wallets$'))
    application.add_handler(CallbackQueryHandler(remove_wallet_menu, pattern='^remove_wallet_menu$'))
    application.add_handler(CallbackQueryHandler(remove_wallet_confirm, pattern='^delete_'))
    
    # Handler untuk fitur portfolio (BARU)
    application.add_handler(CallbackQueryHandler(portfolio_start, pattern='^portfolio_start$'))
    application.add_handler(CallbackQueryHandler(get_portfolio, pattern='^portfolio_'))
    
    application.add_handler(CallbackQueryHandler(start, pattern='^main_menu$'))
    
    print("Bot berjalan dengan fitur portfolio...")
    application.run_polling()

if __name__ == '__main__':
    main()
