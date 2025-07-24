# bot.py (Versi Final dengan Perbaikan Unpack)

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

GET_ADDRESS, SELECT_CHAIN = range(2)

def make_rpc_request(rpc_url, method, params):
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    try:
        response = requests.post(rpc_url, json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logging.error(f"Error saat melakukan request ke RPC: {e}")
    return None

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
    text = f"Halo {user.mention_html()}!\n\nSaya EVM Lens Bot, siap membantumu. Pilih menu di bawah."
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(text=text, reply_markup=get_main_menu_keyboard(), parse_mode='HTML')
    else:
        await update.message.reply_html(text, reply_markup=get_main_menu_keyboard())
    return ConversationHandler.END

async def my_wallets(update: Update, context):
    query = update.callback_query; await query.answer()
    wallets = database.get_wallets_by_user(update.effective_user.id)
    text = "Berikut wallet yang Anda pantau:\n\n" if wallets else "Anda belum menambahkan wallet."
    for _, address, chain in wallets: text += f"🔹 <b>{chain.title()}</b>: <code>{address}</code>\n"
    keyboard = [[InlineKeyboardButton("⬅️ Kembali", callback_data='main_menu')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def remove_wallet_menu(update: Update, context):
    query = update.callback_query; await query.answer()
    wallets = database.get_wallets_by_user(update.effective_user.id)
    if not wallets:
        await query.edit_message_text("Tidak ada wallet untuk dihapus.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Kembali", callback_data='main_menu')]]))
        return
    keyboard = [[InlineKeyboardButton(f"❌ Hapus {c.title()}: {a[:6]}...{a[-4:]}", callback_data=f"delete_{wid}")] for wid, a, c in wallets]
    keyboard.append([InlineKeyboardButton("⬅️ Kembali", callback_data='main_menu')])
    await query.edit_message_text("Pilih wallet yang ingin dihapus:", reply_markup=InlineKeyboardMarkup(keyboard))

async def remove_wallet_confirm(update: Update, context):
    query = update.callback_query; await query.answer()
    wallet_id_to_delete = int(query.data.split('_')[1])
    success = database.remove_wallet_by_id(wallet_id_to_delete, update.effective_user.id)
    await query.edit_message_text("✅ Wallet berhasil dihapus." if success else "❌ Gagal menghapus wallet.")
    await start(update, context)

async def add_wallet_start(update: Update, context):
    query = update.callback_query; await query.answer()
    await query.edit_message_text(text="Oke, kirim alamat wallet (contoh: 0x...) yang ingin Anda pantau.")
    return GET_ADDRESS

async def get_address(update: Update, context):
    address = update.message.text
    context.user_data['wallet_address_to_add'] = address
    await update.message.reply_text(f"Alamat diterima! Pilih jaringan untuk memantau <code>{address}</code>:", reply_markup=get_network_keyboard(), parse_mode='HTML')
    return SELECT_CHAIN

async def select_chain(update: Update, context):
    query = update.callback_query; await query.answer()
    user_id = update.effective_user.id
    address = context.user_data.get('wallet_address_to_add')
    chain = query.data.split('_')[1]
    if not address:
        await query.edit_message_text("Terjadi kesalahan, mulai lagi.", reply_markup=get_main_menu_keyboard())
        return ConversationHandler.END
    success = database.add_wallet(user_id, address, chain)
    text = f"✅ Berhasil! Wallet <code>{address}</code> sekarang dipantau di jaringan {chain.title()}." if success else f"ℹ️ Wallet <code>{address}</code> sudah ada di daftar pantauan Anda untuk jaringan {chain.title()}."
    await query.edit_message_text(text, parse_mode='HTML')
    await start(update, context)
    return ConversationHandler.END

async def portfolio_start(update: Update, context):
    query = update.callback_query; await query.answer()
    wallets = database.get_wallets_by_user(update.effective_user.id)
    if not wallets:
        await query.edit_message_text("Anda belum memiliki wallet untuk dilihat.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Kembali", callback_data='main_menu')]]))
        return
    keyboard = [[InlineKeyboardButton(f"{c.title()}: {a[:6]}...{a[-4:]}", callback_data=f"portfolio_select_{c}_{a}")] for _, a, c in wallets]
    keyboard.append([InlineKeyboardButton("⬅️ Kembali", callback_data='main_menu')])
    await query.edit_message_text("Pilih wallet yang ingin Anda lihat portfolionya:", reply_markup=InlineKeyboardMarkup(keyboard))

async def portfolio_select_asset_type(update: Update, context):
    query = update.callback_query; await query.answer()
    
    # --- PERBAIKAN UTAMA DI SINI ---
    # Kita pecah datanya menjadi 4 bagian, bukan 3.
    try:
        _, _, chain, address = query.data.split('_', 3)
    except ValueError:
        logging.error(f"Gagal unpack callback_data: {query.data}")
        await query.edit_message_text("Terjadi error. Silakan coba lagi dari /start.")
        return
    # --- AKHIR PERBAIKAN ---

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
    await query.edit_message_text("⏳ Sedang mengambil data token, mohon tunggu...")
    _, _, chain, address = query.data.split('_', 3)
    
    chain_data = CHAIN_CONFIG.get(chain, {})
    explorer_url = chain_data.get('explorer_url')
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
                    symbol = metadata.get('symbol', 'UNKNOWN')
                    decimals = metadata.get('decimals', 18)
                    balance = int(balance_hex, 16) / (10 ** decimals)
                    if balance > 0.000001:
                        token_url = f"{explorer_url}/token/{token['contractAddress']}" if explorer_url else "#"
                        text += f"🔹 <a href='{token_url}'><b>{symbol}</b></a>: {balance:,.6f}\n"
                        text += f"   └ <code>{token['contractAddress']}</code>\n\n"
    if not found_tokens: text += "Tidak ada token ERC-20 yang ditemukan.\n"
    keyboard = [[InlineKeyboardButton("⬅️ Kembali ke Menu", callback_data='main_menu')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def get_portfolio_nft(update: Update, context):
    query = update.callback_query; await query.answer()
    await query.edit_message_text("⏳ Sedang mengambil data NFT, mohon tunggu...")
    _, _, chain, address = query.data.split('_', 3)
    
    network_subdomain = CHAIN_CONFIG.get(chain, {}).get('rpc_subdomain')
    explorer_url = CHAIN_CONFIG.get(chain, {}).get('explorer_url')
    if not network_subdomain:
        await query.edit_message_text("Jaringan tidak didukung untuk NFT.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Kembali", callback_data='main_menu')]]))
        return

    api_url = f"https://{network_subdomain}.g.alchemy.com/nft/v3/{config.ALCHEMY_API_KEY}/getNFTsForOwner?owner={address}"
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        logging.error(f"Gagal mengambil data NFT: {e}")
        await query.edit_message_text("Gagal mengambil data NFT dari Alchemy.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Kembali", callback_data='main_menu')]]))
        return

    text = f"<b>🖼️ Portfolio NFT untuk <code>{address}</code> ({chain.title()})</b>\n\n"
    if data and data.get('ownedNfts'):
        collections = {}
        for nft in data['ownedNfts']:
            collection_name = nft.get('collection', {}).get('name', 'Koleksi Tidak Dikenal')
            if collection_name not in collections:
                collections[collection_name] = []
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

def main():
    database.setup_database()
    application = Application.builder().token(config.TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_wallet_start, pattern='^add_wallet_start$')],
        states={ GET_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_address)], SELECT_CHAIN: [CallbackQueryHandler(select_chain, pattern='^chain_')] },
        fallbacks=[CallbackQueryHandler(start, pattern='^main_menu$'), CommandHandler('start', start)]
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(my_wallets, pattern='^my_wallets$'))
    application.add_handler(CallbackQueryHandler(remove_wallet_menu, pattern='^remove_wallet_menu$'))
    application.add_handler(CallbackQueryHandler(remove_wallet_confirm, pattern='^delete_'))
    application.add_handler(CallbackQueryHandler(portfolio_start, pattern='^portfolio_start$'))
    application.add_handler(CallbackQueryHandler(portfolio_select_asset_type, pattern='^portfolio_select_'))
    application.add_handler(CallbackQueryHandler(get_portfolio_erc20, pattern='^portfolio_erc20_'))
    application.add_handler(CallbackQueryHandler(get_portfolio_nft, pattern='^portfolio_nft_'))
    application.add_handler(CallbackQueryHandler(start, pattern='^main_menu$'))
    
    print("Bot berjalan dengan perbaikan alur portfolio...")
    application.run_polling()

if __name__ == '__main__':
    main()
