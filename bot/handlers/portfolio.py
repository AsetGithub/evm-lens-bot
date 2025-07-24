# bot/handlers/portfolio.py

import logging
import requests  # ADDED: Missing import
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
    keyboard = [[InlineKeyboardButton(f"{(alias or (a[:6]+'...'+a[-4:]))} ({c.title()})", callback_data=f"portfolio_select_{wid}")] for wid, a, c, alias in wallets]
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
    """Menampilkan portfolio Token ERC-20 dengan nilai USD."""
    query = update.callback_query; await query.answer()
    await query.edit_message_text("⏳ Sedang mengambil data token & harga...")
    wallet_id = int(query.data.split('_')[2])
    wallet_data = database.get_wallet_by_id(wallet_id, update.effective_user.id)
    if not wallet_data:
        await query.edit_message_text("Wallet tidak ditemukan.")
        return
    address, chain = wallet_data
    chain_data = CHAIN_CONFIG.get(chain, {}); explorer_url = chain_data.get('explorer_url')
    rpc_url = f"https://{chain_data['rpc_subdomain']}.g.alchemy.com/v2/{config.ALCHEMY_API_KEY}"
    
    # Ambil saldo native
    native_balance_hex = make_rpc_request(rpc_url, "eth_getBalance", [address, "latest"]).get('result', '0x0')
    native_balance = int(native_balance_hex, 16) / 1e18
    native_symbol = chain_data.get('symbol', 'NATIVE')
    
    params = [address, "erc20"]
    response = make_rpc_request(rpc_url, "alchemy_getTokenBalances", params)
    
    text = f"<b>💰 Portfolio Token untuk <code>{address}</code> ({chain.title()})</b>\n\n"
    total_usd_value = 0
    
    # Tampilkan saldo native dulu
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
                        # Di masa depan, kita bisa cari harga token ini
                        text += f"🔹 {balance:,.6f} {symbol}\n"
    
    text += f"\n---\n💰 **Total Estimasi Nilai: ${total_usd_value:,.2f}**"
    keyboard = [[InlineKeyboardButton("⬅️ Kembali ke Menu", callback_data='main_menu')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def get_portfolio_nft(update: Update, context):
    """Menampilkan portfolio NFT dengan harga dasar."""
    query = update.callback_query; await query.answer()
    await query.edit_message_text("⏳ Sedang mengambil data NFT & harga dasar...")
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
        
    api_url = f"https://{network_subdomain}.g.alchemy.com/nft/v3/{config.ALCHEMY_API_KEY}/getNFTsForOwner?owner={address}&withMetadata=true"
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
            contract_address = nfts[0].get('contract', {}).get('address')
            floor_price_text = ""
            if contract_address:
                floor_api_url = f"https://{network_subdomain}.g.alchemy.com/nft/v3/{config.ALCHEMY_API_KEY}/getFloorPrice?contractAddress={contract_address}"
                try:
                    floor_res = requests.get(floor_api_url).json()
                    if floor_res.get('openSea', {}).get('floorPrice'):
                        fp = floor_res['openSea']['floorPrice']
                        sym = floor_res['openSea']['priceCurrency']
                        floor_price_text = f"(Floor: {fp} {sym})"
                except: pass
            
            text += f"<b> koleksi {name}</b> {floor_price_text}\n"
            for nft in nfts[:3]:
                nft_name = nft.get('name') or f"#{nft.get('tokenId')}"
                text += f"  - {nft_name}\n"
            if len(nfts) > 3: text += "  - ...dan lainnya\n"
            text += "\n"
    else:
        text += "Tidak ada NFT yang ditemukan.\n"
        
    keyboard = [[InlineKeyboardButton("⬅️ Kembali ke Menu", callback_data='main_menu')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML', disable_web_page_preview=True)