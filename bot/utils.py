# bot/utils.py

import requests
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from monitor import CHAIN_CONFIG

def make_rpc_request(rpc_url, method, params):
    """Fungsi pembantu untuk membuat permintaan JSON-RPC."""
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    try:
        response = requests.post(rpc_url, json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logging.error(f"Error saat melakukan request ke RPC: {e}")
    return None

def get_price(coingecko_id):
    """Mengambil harga dari CoinGecko API."""
    if not coingecko_id: return None
    try:
        url = f"[https://api.coingecko.com/api/v3/simple/price?ids=](https://api.coingecko.com/api/v3/simple/price?ids=){coingecko_id}&vs_currencies=usd"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data.get(coingecko_id, {}).get('usd')
    except Exception as e:
        logging.error(f"Gagal mengambil harga untuk {coingecko_id}: {e}")
    return None

def get_main_menu_keyboard():
    """Membuat keyboard untuk menu utama."""
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
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("❌ Batalkan", callback_data='cancel')])
    return InlineKeyboardMarkup(keyboard)
