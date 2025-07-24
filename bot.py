# bot.py (Versi Final dengan Perbaikan Tampilan Alias)

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
GET_ADDRESS, SELECT_CHAIN, GET_ALIAS = range(3)
SET_MIN_VALUE = range(3, 4)

def make_rpc_request(rpc_url, method, params):
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    try:
        response = requests.post(rpc_url, json=payload); response.raise_for_status()
        return response.json()
    except Exception as e:
        logging.error(f"Error RPC: {e}")
    return None

def get_main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("➕ Tambah Wallet", callback_data='add_wallet_start')],
        [
            InlineKeyboardButton("📂 Wallet Saya", callback_data='my_wallets'),
            InlineKeyboardButton("🗑️ Hapus Wallet", callback_data='remove_wallet_menu')
        ],
        [InlineKeyboardButton("📊 Cek Portfolio", callback_data='portfolio_start')],
        [InlineKeyboardButton("⚙️ Pengaturan Notifikasi", callback_data='settings_menu')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_network_keyboard():
    keyboard = []
    row = []
    for chain in CHAIN_CONFIG.keys():
        row.append(InlineKeyboardButton(chain.title(), callback_data=f"chain_{chain}"))
        if len(row) == 3: keyboard.append(row); row = []
    if row: keyboard.append(row)
    keyboard.append([InlineKeyboardButton("❌ Batalkan", callback_data='cancel')])
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context):
    user = update.effective_user
    text = f"Halo {user.mention_html()}!\n\nSelamat datang di EVM Lens Bot. Siap membantumu memantau aset Web3. Pilih menu di bawah."
    if update.callback_query:
        query = update.callback_query; await query.answer()
        await query.edit_message_text(text=text, reply_markup=get_main_menu_keyboard(), parse_mode='HTML')
    else:
        await update.message.reply_html(text, reply_markup=get_main_menu_keyboard())
    return ConversationHandler.END

async def add_wallet_start(update: Update, context):
    query = update.callback_query; await query.answer()
    await query.edit_message_text(text="✍️ Oke, kirim alamat wallet (contoh: 0x...) yang ingin Anda pantau.")
    return GET_ADDRESS

async def get_address(update: Update, context):
    context.user_data['address'] = update.message.text
    await update.message.reply_text("🌐 Alamat diterima! Sekarang pilih jaringannya:", reply_markup=get_network_keyboard())
    return SELECT_CHAIN

async def select_chain(update: Update, context):
    query = update.callback_query; await query.answer()
    context.user_data['chain'] = query.data.split('_')[1]
    await query.edit_message_text("📝 Terakhir, beri nama alias untuk wallet ini (contoh: Dompet Utama). Kirim /skip untuk menggunakan alamat sebagai nama.")
    return GET_ALIAS

async def get_alias(update: Update, context):
    alias = update.message.text
    user_id = update.effective_user.id
    address = context.user_data['address']
    chain = context.user_data['chain']
    success = database.add_wallet(user_id, address, chain, alias)
    text = f"✅ Berhasil! Wallet '{alias}' sekarang dipantau di jaringan {chain.title()}." if success else f"ℹ️ Wallet ini sudah ada di daftar pantauan Anda."
    await update.message.reply_text(text)
    await start(update, context)
    return ConversationHandler.END

async def skip_alias(update: Update, context):
    address = context.user_data['address']
    alias = f"{address[:6]}...{address[-4:]}"
    update.message.text = alias
    return await get_alias(update, context)

async def my_wallets(update: Update, context):
    query = update.callback_query; await query.answer()
    wallets = database.get_wallets_by_user(update.effective_user.id)
    text = "📂 **Wallet Anda:**\n\n" if wallets else "Anda belum menambahkan wallet."
    for _, address, chain, alias in wallets:
        # --- PERBAIKAN DI SINI ---
        display_name = alias if alias else f"{address[:6]}...{address[-4:]}"
        # --- AKHIR PERBAIKAN ---
        text += f"🔹 **{display_name}** ({chain.title()})\n   └ <code>{address}</code>\n"
    keyboard = [[InlineKeyboardButton("⬅️ Kembali", callback_data='main_menu')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def remove_wallet_menu(update: Update, context):
    query = update.callback_query; await query.answer()
    wallets = database.get_wallets_by_user(update.effective_user.id)
    if not wallets:
        await query.edit_message_text("Tidak ada wallet untuk dihapus.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Kembali", callback_data='main_menu')]]))
        return
    keyboard = []
    for wid, address, chain, alias in wallets:
        display_name = alias if alias else f"{address[:6]}...{address[-4:]}"
        keyboard.append([InlineKeyboardButton(f"❌ Hapus '{display_name}' ({chain.title()})", callback_data=f"delete_{wid}")])
    keyboard.append([InlineKeyboardButton("⬅️ Kembali", callback_data='main_menu')])
    await query.edit_message_text("Pilih wallet yang ingin dihapus:", reply_markup=InlineKeyboardMarkup(keyboard))

async def remove_wallet_confirm(update: Update, context):
    query = update.callback_query; await query.answer()
    wallet_id_to_delete = int(query.data.split('_')[1])
    success = database.remove_wallet_by_id(wallet_id_to_delete, update.effective_user.id)
    await query.edit_message_text("✅ Wallet berhasil dihapus." if success else "❌ Gagal menghapus wallet.")
    await start(update, context)

async def portfolio_start(update: Update, context):
    query = update.callback_query; await query.answer()
    wallets = database.get_wallets_by_user(update.effective_user.id)
    if not wallets:
        await query.edit_message_text("Anda belum memiliki wallet untuk dilihat.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Kembali", callback_data='main_menu')]]))
        return
    keyboard = []
    for _, address, chain, alias in wallets:
        display_name = alias if alias else f"{address[:6]}...{address[-4:]}"
        keyboard.append([InlineKeyboardButton(f"{display_name} ({chain.title()})", callback_data=f"portfolio_select_{chain}_{address}")])
    keyboard.append([InlineKeyboardButton("⬅️ Kembali", callback_data='main_menu')])
    await query.edit_message_text("Pilih wallet yang ingin Anda lihat portfolionya:", reply_markup=InlineKeyboardMarkup(keyboard))

async def portfolio_select_asset_type(update: Update, context):
    query = update.callback_query; await query.answer()
    try:
        _, _, chain, address = query.data.split('_', 3)
    except ValueError:
        logging.error(f"Gagal unpack callback_data: {query.data}")
        await query.edit_message_text("Terjadi error. Silakan coba lagi dari /start.")
        return
    text = f"Pilih jenis aset untuk wallet <code>{address[:10]}...</code> di jaringan {chain.title()}:"
    keyboard = [
        [
            InlineKeyboardButton("💰 Token (ERC-20)", callback_data=f"portfolio_erc20_{chain}_{address}"),
            InlineKeyboardButton("🖼️ Koleksi NFT", callback_data=f"portfolio_nft_{chain}_{address}")
        ],
        [InlineKeyboardButton("⬅️ Kembali", callback_data='main_menu')]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def get_portfolio_erc20(update: Update, context):
    query = update.callback_query; await query.answer()
    await query.edit_message_text("⏳ Sedang mengambil data token...")
    _, _, chain, address = query.data.split('_', 3)
    chain_data = CHAIN_CONFIG.get(chain, {}); explorer_url = chain_data.get('explorer_url')
    rpc_url = f"https://{chain_data['rpc_subdomain']}.g.alchemy.com/v2/{config.ALCHEMY_API_KEY}"
    params = [address, "erc20"]
    response = make_rpc_request(rpc_url, "alchemy_getTokenBalances", params)
    text = f"<b>💰 Portfolio Token untuk <code>{address}</code> ({chain.title()})</b>\n\n"
    found_tokens = False
    if response and 'result' in response and response['result'].get('tokenBalances'):
        for token in response['result']['tokenBalances']:
            balance_hex = token.get('tokenBalance', '0x0')
            if balance_hex and int(balance_hex, 16) > 0:
                found_tokens = True
                metadata_response = make_rpc_request(rpc_url, "alchemy_getTokenMetadata", [token['contractAddress']])
                if metadata_response and 'result' in metadata_response:
                    metadata = metadata_response['result']
                    symbol = metadata.get('symbol', 'UNKNOWN'); decimals = metadata.get('decimals', 18)
                    balance = int(balance_hex, 16) / (10 ** decimals)
                    if balance > 0.000001:
                        token_url = f"{explorer_url}/token/{token['contractAddress']}" if explorer_url else "#"
                        text += f"🔹 <a href='{token_url}'><b>{symbol}</b></a>: {balance:,.6f}\n   └ <code>{token['contractAddress']}</code>\n\n"
    if not found_tokens: text += "Tidak ada token ERC-20 yang ditemukan.\n"
    keyboard = [[InlineKeyboardButton("⬅️ Kembali ke Menu", callback_data='main_menu')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def get_portfolio_nft(update: Update, context):
    query = update.callback_query; await query.answer()
    await query.edit_message_text("⏳ Sedang mengambil data NFT...")
    _, _, chain, address = query.data.split('_', 3)
    network_subdomain = CHAIN_CONFIG.get(chain, {}).get('rpc_subdomain')
    explorer_url = CHAIN_CONFIG.get(chain, {}).get('explorer_url')
    if not network_subdomain:
        await query.edit_message_text("Jaringan tidak didukung untuk NFT.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Kembali", callback_data='main_menu')]]))
        return
    api_url = f"https://{network_subdomain}.g.alchemy.com/nft/v3/{config.ALCHEMY_API_KEY}/getNFTsForOwner?owner={address}"
    try:
        response = requests.get(api_url); response.raise_for_status(); data = response.json()
    except Exception as e:
        logging.error(f"Gagal mengambil data NFT: {e}")
        await query.edit_message_text("Gagal mengambil data NFT.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Kembali", callback_data='main_menu')]]))
        return
    text = f"<b>🖼️ Portfolio NFT untuk <code>{address}</code> ({chain.title()})</b>\n\n"
    if data and data.get('ownedNfts'):
        collections = {}
        for nft in data['ownedNfts']:
            collection_name = nft.get('collection', {}).get('name', 'Koleksi Tidak Dikenal')
            if collection_name not in collections: collections[collection_name] = []
            collections[collection_name].append(nft)
        for name, nfts in collections.items():
            text += f"<b> collezione {name}</b> ({len(nfts)} NFT)\n"
            for nft in nfts[:3]:
                nft_name = nft.get('name', f"#{nft.get('tokenId')}")
                nft_url = f"{explorer_url}/nft/{nft['contract']['address']}/{nft['tokenId']}" if explorer_url else "#"
                text += f"  - <a href='{nft_url}'>{nft_name}</a>\n"
            if len(nfts) > 3: text += "  - ...dan lainnya\n"
            text += "\n"
    else:
        text += "Tidak ada NFT yang ditemukan.\n"
    keyboard = [[InlineKeyboardButton("⬅️ Kembali ke Menu", callback_data='main_menu')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML', disable_web_page_preview=True)

async def settings_menu(update: Update, context):
    query = update.callback_query; await query.answer()
    user_id = update.effective_user.id
    settings = database.get_user_settings(user_id)
    min_val_text = f"${settings['min_value_usd']}" if settings['min_value_usd'] > 0 else "Tidak ada"
    airdrop_text = "✅ Aktif" if settings['notify_on_airdrop'] else "❌ Nonaktif"
    text = f"**⚙️ Pengaturan Notifikasi**\n\n- **Nilai Minimum:** {min_val_text}\n- **Notifikasi Airdrop:** {airdrop_text}"
    keyboard = [
        [InlineKeyboardButton("💲 Ubah Nilai Minimum", callback_data='set_min_value_start')],
        [InlineKeyboardButton(f"Toggle Airdrop ({'Matikan' if settings['notify_on_airdrop'] else 'Aktifkan'})", callback_data='toggle_airdrop')],
        [InlineKeyboardButton("⬅️ Kembali", callback_data='main_menu')]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def set_min_value_start(update: Update, context):
    query = update.callback_query; await query.answer()
    await query.edit_message_text("Masukkan nilai minimum transaksi dalam USD (contoh: 50). Kirim 0 untuk menonaktifkan.")
    return SET_MIN_VALUE

async def set_min_value_received(update: Update, context):
    try:
        value = float(update.message.text)
        database.update_user_setting(update.effective_user.id, 'min_value_usd', value)
        await update.message.reply_text(f"✅ Nilai minimum berhasil diatur ke ${value}.")
    except ValueError:
        await update.message.reply_text("❌ Input tidak valid. Harap masukkan angka.")
    await start(update, context)
    return ConversationHandler.END

async def toggle_airdrop(update: Update, context):
    query = update.callback_query; await query.answer()
    user_id = update.effective_user.id
    settings = database.get_user_settings(user_id)
    new_value = not settings['notify_on_airdrop']
    database.update_user_setting(user_id, 'notify_on_airdrop', new_value)
    await settings_menu(update, context)

def main():
    database.setup_database()
    application = Application.builder().token(config.TELEGRAM_TOKEN).build()
    add_wallet_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_wallet_start, pattern='^add_wallet_start$')],
        states={
            GET_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_address)],
            SELECT_CHAIN: [CallbackQueryHandler(select_chain, pattern='^chain_')],
            GET_ALIAS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_alias), CommandHandler('skip', skip_alias)],
        },
        fallbacks=[CommandHandler('start', start), CallbackQueryHandler(start, pattern='^main_menu$')]
    )
    settings_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(set_min_value_start, pattern='^set_min_value_start$')],
        states={ SET_MIN_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_min_value_received)] },
        fallbacks=[CommandHandler('start', start), CallbackQueryHandler(start, pattern='^main_menu$')]
    )
    application.add_handler(CommandHandler("start", start))
    application.add_handler(add_wallet_conv)
    application.add_handler(settings_conv)
    application.add_handler(CallbackQueryHandler(my_wallets, pattern='^my_wallets$'))
    application.add_handler(CallbackQueryHandler(remove_wallet_menu, pattern='^remove_wallet_menu$'))
    application.add_handler(CallbackQueryHandler(remove_wallet_confirm, pattern='^delete_'))
    application.add_handler(CallbackQueryHandler(portfolio_start, pattern='^portfolio_start$'))
    application.add_handler(CallbackQueryHandler(portfolio_select_asset_type, pattern='^portfolio_select_'))
    application.add_handler(CallbackQueryHandler(get_portfolio_erc20, pattern='^portfolio_erc20_'))
    application.add_handler(CallbackQueryHandler(get_portfolio_nft, pattern='^portfolio_nft_'))
    application.add_handler(CallbackQueryHandler(settings_menu, pattern='^settings_menu$'))
    application.add_handler(CallbackQueryHandler(toggle_airdrop, pattern='^toggle_airdrop$'))
    application.add_handler(CallbackQueryHandler(start, pattern='^main_menu$'))
    print("Bot berjalan dengan fitur Alias & Settings...")
    application.run_polling()

if __name__ == '__main__':
    main()
