# bot.py (Versi Final dengan /help dan link Telegraph)

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
        [InlineKeyboardButton("⚙️ Pengaturan Notifikasi", callback_data='settings_menu')],
        [InlineKeyboardButton("⛽ Cek Gas Fee", callback_data='gas_start')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_network_keyboard(callback_prefix):
    """Membuat keyboard jaringan dengan prefix callback yang berbeda."""
    keyboard = []
    row = []
    for chain in CHAIN_CONFIG.keys():
        row.append(InlineKeyboardButton(chain.title(), callback_data=f"{callback_prefix}{chain}"))
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

# --- Perintah Bantuan /help (BARU) ---
async def help_command(update: Update, context):
    # Link Telegraph Anda sudah dimasukkan di sini
    telegraph_url = "https://telegra.ph/Selamat-Datang-di-EVM-Lens-Bot-Beta-07-24" 
    
    text = (
        "❓ **Bantuan EVM Lens Bot**\n\n"
        "Berikut adalah fungsi utama yang bisa Anda gunakan melalui menu:\n\n"
        "🔹 **Tambah/Hapus Wallet:** Kelola daftar wallet yang Anda pantau.\n"
        "🔹 **Cek Portfolio:** Lihat daftar lengkap Token (ERC-20) dan koleksi NFT.\n"
        "🔹 **Pengaturan Notifikasi:** Atur preferensi notifikasi Anda.\n"
        "🔹 **Cek Gas Fee:** Periksa biaya transaksi di berbagai jaringan.\n\n"
        "Untuk informasi lebih detail, roadmap, dan info tentang author, silakan kunjungi halaman informasi kami."
    )
    
    keyboard = [[InlineKeyboardButton("📖 Baca Info Lengkap & Roadmap", url=telegraph_url)]]
    
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def add_wallet_start(update: Update, context):
    query = update.callback_query; await query.answer()
    await query.edit_message_text(text="✍️ Oke, kirim alamat wallet (contoh: 0x...) yang ingin Anda pantau.")
    return GET_ADDRESS

async def get_address(update: Update, context):
    context.user_data['address'] = update.message.text
    await update.message.reply_text("🌐 Alamat diterima! Sekarang pilih jaringannya:", reply_markup=get_network_keyboard('chain_'))
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
        display_name = alias if alias else f"{address[:6]}...{address[-4:]}"
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
    keyboard = [[InlineKeyboardButton(f"{(alias or (a[:6]+'...'+a[-4:]))} ({c.title()})", callback_data=f"portfolio_select_{wid}")] for wid, a, c, alias in wallets]
    keyboard.append([InlineKeyboardButton("⬅️ Kembali", callback_data='main_menu')])
    await query.edit_message_text("Pilih wallet yang ingin Anda lihat portfolionya:", reply_markup=InlineKeyboardMarkup(keyboard))

async def portfolio_select_asset_type(update: Update, context):
    query = update.callback_query; await query.answer()
    try:
        wallet_id = int(query.data.split('_')[2])
        wallet_data = database.get_wallet_by_id(wallet_id, update.effective_user.id)
        if not wallet_data:
            await query.edit_message_text("Wallet tidak ditemukan.")
            return
        address, chain = wallet_data
    except (ValueError, IndexError):
        await query.edit_message_text("Data tombol tidak valid.")
        return
    text = f"Pilih jenis aset untuk wallet <code>{address[:10]}...</code> di jaringan {chain.title()}:"
    keyboard = [
        [
            InlineKeyboardButton("💰 Token (ERC-20)", callback_data=f"portfolio_erc20_{wallet_id}"),
            InlineKeyboardButton("🖼️ Koleksi NFT", callback_data=f"portfolio_nft_{wallet_id}")
        ],
        [InlineKeyboardButton("⬅️ Kembali", callback_data='main_menu')]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def get_portfolio_erc20(update: Update, context):
    query = update.callback_query; await query.answer()
    await query.edit_message_text("⏳ Sedang mengambil data token...")
    wallet_id = int(query.data.split('_')[2])
    wallet_data = database.get_wallet_by_id(wallet_id, update.effective_user.id)
    if not wallet_data:
        await query.edit_message_text("Wallet tidak ditemukan.")
        return
    address, chain = wallet_data
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
    wallet_id = int(query.data.split('_')[2])
    wallet_data = database.get_wallet_by_id(wallet_id, update.effective_user.id)
    if not wallet_data:
        await query.edit_message_text("Wallet tidak ditemukan.")
        return
    address, chain = wallet_data
    network_subdomain = CHAIN_CONFIG.get(chain, {}).get('rpc_subdomain')
    explorer_url = CHAIN_CONFIG.get(chain, {}).get('explorer_url')
    if not network_subdomain:
        await query.edit_message_text("Jaringan tidak didukung untuk NFT.")
        return
    api_url = f"https://{network_subdomain}.g.alchemy.com/nft/v3/{config.ALCHEMY_API_KEY}/getNFTsForOwner?owner={address}"
    try:
        response = requests.get(api_url); response.raise_for_status(); data = response.json()
    except Exception as e:
        logging.error(f"Gagal mengambil data NFT: {e}")
        await query.edit_message_text("Gagal mengambil data NFT.")
        return
    text = f"<b>🖼️ Portfolio NFT untuk <code>{address}</code> ({chain.title()})</b>\n\n"
    if data and data.get('ownedNfts'):
        collections = {}
        for nft in data['ownedNfts']:
            collection_info = nft.get('collection')
            if collection_info: collection_name = collection_info.get('name', 'Koleksi Tidak Dikenal')
            else: collection_name = 'Koleksi Tidak Dikenal'
            if collection_name not in collections: collections[collection_name] = []
            collections[collection_name].append(nft)
        for name, nfts in collections.items():
            text += f"<b> koleksi {name}</b> ({len(nfts)} NFT)\n"
            for nft in nfts[:5]:
                nft_name = nft.get('name') or f"#{nft.get('tokenId')}"
                contract_address = nft.get('contract', {}).get('address')
                token_id = nft.get('tokenId')
                if explorer_url and contract_address and token_id:
                    nft_url = f"{explorer_url}/nft/{contract_address}/{token_id}"
                    text += f"  - <a href='{nft_url}'>{nft_name}</a>\n"
                else: text += f"  - {nft_name}\n"
            if len(nfts) > 5: text += "  - ...dan lainnya\n"
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

async def gas_start(update: Update, context):
    """Memulai alur pengecekan gas, menampilkan pilihan jaringan."""
    if update.callback_query:
        query = update.callback_query; await query.answer()
        await query.edit_message_text(text="⛽ Pilih jaringan untuk memeriksa gas fee:", reply_markup=get_network_keyboard('gas_'))
    else: # Jika dari command /gas
        await update.message.reply_text(text="⛽ Pilih jaringan untuk memeriksa gas fee:", reply_markup=get_network_keyboard('gas_'))

async def get_gas_price(update: Update, context):
    """Mengambil dan menampilkan harga gas untuk jaringan yang dipilih."""
    query = update.callback_query; await query.answer()
    chain = query.data.split('_')[1]
    await query.edit_message_text(f"⏳ Sedang memeriksa gas fee di jaringan {chain.title()}...")
    chain_data = CHAIN_CONFIG.get(chain, {})
    rpc_url = f"https://{chain_data['rpc_subdomain']}.g.alchemy.com/v2/{config.ALCHEMY_API_KEY}"
    response = make_rpc_request(rpc_url, "eth_gasPrice", [])
    if response and 'result' in response:
        gas_price_wei = int(response['result'], 16)
        gas_price_gwei = gas_price_wei / 1e9
        text = f"⛽ **Gas Fee Saat Ini ({chain.title()})**\n\n🔹 **{gas_price_gwei:.2f} Gwei**"
    else:
        text = f"❌ Gagal mengambil data gas fee untuk jaringan {chain.title()}."
    keyboard = [
        [InlineKeyboardButton("🔎 Cek Jaringan Lain", callback_data='gas_start')],
        [InlineKeyboardButton("⬅️ Kembali ke Menu Utama", callback_data='main_menu')]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

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
    application.add_handler(CommandHandler("help", help_command)) # Tambahkan handler /help
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
    application.add_handler(CommandHandler("gas", gas_start))
    application.add_handler(CallbackQueryHandler(gas_start, pattern='^gas_start$'))
    application.add_handler(CallbackQueryHandler(get_gas_price, pattern='^gas_'))
    application.add_handler(CallbackQueryHandler(start, pattern='^main_menu$'))
    
    print("Bot berjalan dengan semua fitur profesional...")
    application.run_polling()

if __name__ == '__main__':
    main()
    
