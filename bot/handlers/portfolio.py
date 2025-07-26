# bot/handlers/portfolio.py - VERSI LENGKAP DAN FINAL

import logging
import requests
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
import database
import config
from constants import CHAIN_CONFIG
from bot.utils import make_rpc_request, get_price

async def portfolio_start(update: Update, context):
    """Langkah 1 Portfolio: Menampilkan daftar wallet untuk dipilih."""
    query = update.callback_query; await query.answer()
    wallets = database.get_wallets_by_user(update.effective_user.id)
    
    if not wallets:
        await query.edit_message_text("Anda belum memiliki wallet untuk dilihat.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Kembali", callback_data='main_menu')]]))
        return
    
    keyboard = []
    for wallet in wallets:
        wid = wallet['id']
        chain = wallet['chain']
        alias = wallet['alias']
        display_name = f"{alias} ({chain.title()})"
        keyboard.append([InlineKeyboardButton(display_name, callback_data=f"portfolio_select_{wid}")])

    keyboard.append([InlineKeyboardButton("⬅️ Kembali", callback_data='main_menu')])
    await query.edit_message_text("Pilih wallet yang ingin Anda lihat portfolionya:", reply_markup=InlineKeyboardMarkup(keyboard))

async def portfolio_select_asset_type(update: Update, context):
    """Langkah 2 Portfolio: Meminta pengguna memilih jenis aset."""
    query = update.callback_query; await query.answer()
    try:
        wallet_id = int(query.data.split('_')[2])
        wallet_data = database.get_wallet_by_id(wallet_id, update.effective_user.id)
        if not wallet_data:
            await query.edit_message_text("Wallet tidak ditemukan.")
            return
        address = wallet_data['address']
        chain = wallet_data['chain']
        
    except (ValueError, IndexError, KeyError):
        await query.edit_message_text("Data tombol tidak valid.")
        return
        
    text = f"Pilih jenis aset untuk wallet <code>{address[:10]}...</code> di jaringan {chain.title()}:"
    keyboard = [
        [
            InlineKeyboardButton("💰 Token (ERC-20)", callback_data=f"portfolio_erc20_{wallet_id}"),
            InlineKeyboardButton("🖼️ Koleksi NFT", callback_data=f"portfolio_nft_{wallet_id}")
        ],
        [InlineKeyboardButton("⬅️ Kembali", callback_data='portfolio_start')]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def get_portfolio_erc20(update: Update, context):
    """Menampilkan portfolio Token ERC-20 dengan nilai USD."""
    query = update.callback_query; await query.answer()
    await query.edit_message_text("⏳ Sedang mengambil data token & harga...")
    wallet_id = int(query.data.split('_')[2])
    
    wallet_data = database.get_wallet_by_id(wallet_id, update.effective_user.id)
    if not wallet_data:
        await query.edit_message_text("Wallet tidak ditemukan.")
        return
    address = wallet_data['address']
    chain = wallet_data['chain']
    
    chain_data = CHAIN_CONFIG.get(chain, {});
    rpc_url = f"https://{chain_data['rpc_subdomain']}.g.alchemy.com/v2/{config.ALCHEMY_API_KEY}"
    
    native_balance_hex = make_rpc_request(rpc_url, "eth_getBalance", [address, "latest"]).get('result', '0x0')
    native_balance = int(native_balance_hex, 16) / 1e18
    native_symbol = chain_data.get('symbol', 'NATIVE')
    
    params = [address, "erc20"]
    response = make_rpc_request(rpc_url, "alchemy_getTokenBalances", params)
    
    text = f"<b>💰 Portfolio Token untuk <code>{address}</code> ({chain.title()})</b>\n\n"
    total_usd_value = 0
    
    if native_balance > 0.000001:
        native_price = get_price(chain_data.get('coingecko_id'))
        usd_value = native_balance * native_price if native_price else 0
        total_usd_value += usd_value
        usd_text = f" (~${usd_value:,.2f})" if usd_value > 0 else ""
        text += f"🔹 <b>{native_balance:,.6f} {native_symbol}</b>{usd_text}\n\n"

    if response and 'result' in response and response['result'].get('tokenBalances'):
        for token in response['result']['tokenBalances']:
            balance_hex = token.get('tokenBalance', '0x0')
            if balance_hex and int(balance_hex, 16) > 0:
                metadata_response = make_rpc_request(rpc_url, "alchemy_getTokenMetadata", [token['contractAddress']])
                if metadata_response and 'result' in metadata_response:
                    metadata = metadata_response['result']
                    symbol = metadata.get('symbol', 'UNKNOWN'); decimals = metadata.get('decimals', 18)
                    balance = int(balance_hex, 16) / (10 ** decimals)
                    if balance > 0.000001:
                        text += f"🔹 {balance:,.6f} {symbol}\n"
    
    text += f"\n---\n💰 **Total Estimasi Nilai: ${total_usd_value:,.2f}**"
    keyboard = [[InlineKeyboardButton("⬅️ Kembali", callback_data=f"portfolio_select_{wallet_id}")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def get_portfolio_nft(update: Update, context):
    """Menampilkan portfolio NFT dengan harga dasar."""
    query = update.callback_query; await query.answer()
    await query.edit_message_text("⏳ Sedang mengambil data NFT...")
    wallet_id = int(query.data.split('_')[2])
    
    wallet_data = database.get_wallet_by_id(wallet_id, update.effective_user.id)
    if not wallet_data:
        await query.edit_message_text("Wallet tidak ditemukan.")
        return
        
    address = wallet_data['address']
    chain = wallet_data['chain']
    
    network_subdomain = CHAIN_CONFIG.get(chain, {}).get('rpc_subdomain')
    if not network_subdomain:
        await query.edit_message_text("Jaringan tidak didukung untuk NFT.")
        return
        
    # Menggunakan URL API v2 yang lebih stabil untuk multi-chain
    api_url = f"https://{network_subdomain}.g.alchemy.com/nft/v2/{config.ALCHEMY_API_KEY}/getNFTs?owner={address}&withMetadata=true"
    
    try:
        response = requests.get(api_url, timeout=15)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Gagal mengambil data NFT: {e}")
        await query.edit_message_text("Gagal mengambil data NFT dari server. Silakan coba lagi nanti.")
        return
        
    text = f"<b>🖼️ Portfolio NFT untuk <code>{address}</code> ({chain.title()})</b>\n\n"
    if data and data.get('ownedNfts'):
        collections = {}
        for nft in data['ownedNfts']:
            collection_name = nft.get('contract', {}).get('name', 'Koleksi Tidak Dikenal')
            if collection_name not in collections:
                collections[collection_name] = []
            collections[collection_name].append(nft)
        
        for name, nfts in collections.items():
            text += f"<b>Koleksi: {name}</b> ({len(nfts)} item)\n"
            for nft in nfts[:3]:
                nft_name = nft.get('name') or f"Token ID #{nft.get('tokenId')}"
                text += f"  - {nft_name}\n"
            if len(nfts) > 3:
                text += f"  - ...dan {len(nfts) - 3} lainnya\n"
            text += "\n"
    else:
        text += "Tidak ada NFT yang ditemukan di wallet ini.\n"
        
    keyboard = [[InlineKeyboardButton("⬅️ Kembali", callback_data=f"portfolio_select_{wallet_id}")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML', disable_web_page_preview=True)
