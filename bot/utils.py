# bot/utils.py - Updated dengan Price Alert System
# Indonesia: Utility functions dengan tambahan untuk price alerts

import requests
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from constants import CHAIN_CONFIG

def make_rpc_request(rpc_url, method, params):
    """Indonesia: Fungsi pembantu untuk membuat permintaan JSON-RPC."""
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    try:
        response = requests.post(rpc_url, json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logging.error(f"Error saat melakukan request ke RPC: {e}")
    return None

def get_price(coingecko_id):
    """Indonesia: Mengambil harga dari CoinGecko API."""
    if not coingecko_id: return None
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coingecko_id}&vs_currencies=usd"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data.get(coingecko_id, {}).get('usd')
    except Exception as e:
        logging.error(f"Gagal mengambil harga untuk {coingecko_id}: {e}")
    return None

def get_main_menu_keyboard():
    """Indonesia: Membuat keyboard untuk menu utama dengan Price Alert."""
    keyboard = [
        [InlineKeyboardButton("➕ Tambah Wallet", callback_data='add_wallet_start')],
        [
            InlineKeyboardButton("📂 Wallet Saya", callback_data='my_wallets'),
            InlineKeyboardButton("🗑️ Hapus Wallet", callback_data='remove_wallet_menu')
        ],
        [InlineKeyboardButton("📊 Cek Portfolio", callback_data='portfolio_start')],
        [
            InlineKeyboardButton("🚨 Price Alerts", callback_data='alert_menu'),  # Indonesia: BARU
            InlineKeyboardButton("⛽ Cek Gas Fee", callback_data='gas_start')
        ],
        [InlineKeyboardButton("⚙️ Pengaturan Notifikasi", callback_data='settings_menu')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_network_keyboard(callback_prefix):
    """Indonesia: Membuat keyboard jaringan dengan prefix callback yang berbeda."""
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

def format_price_display(price, decimals=6):
    """Indonesia: Format harga untuk ditampilkan dengan lebih rapi"""
    if price is None:
        return "N/A"
    
    if price >= 1000:
        return f"${price:,.2f}"
    elif price >= 1:
        return f"${price:.4f}"
    else:
        return f"${price:.{decimals}f}"

def get_price_change_emoji(old_price, new_price):
    """Indonesia: Dapatkan emoji berdasarkan perubahan harga"""
    if old_price is None or new_price is None:
        return "📊"
    
    if new_price > old_price:
        return "📈"
    elif new_price < old_price:
        return "📉"
    else:
        return "➡️"

def calculate_percentage_change(old_value, new_value):
    """Indonesia: Hitung persentase perubahan"""
    if old_value is None or new_value is None or old_value == 0:
        return 0
    
    return ((new_value - old_value) / old_value) * 100

def format_percentage_change(percentage):
    """Indonesia: Format persentase perubahan dengan warna"""
    if percentage > 0:
        return f"+{percentage:.2f}%"
    else:
        return f"{percentage:.2f}%"

def get_chain_emoji(chain_name):
    """Indonesia: Dapatkan emoji untuk setiap chain"""
    chain_emojis = {
        'ethereum': '🔷',
        'arbitrum': '🔵',
        'optimism': '🔴',
        'polygon': '🟣',
        'base': '🔵',
        'bsc': '🟡',
        'avalanche': '⚪',
        'fantom': '👻',
        'zksync': '⚫',
        'linea': '🟢',
        'scroll': '📜',
        'blast': '💥',
        'zora': '🎨',
        'mantle': '🧩',
        'cronos': '💎',
        'gnosis': '🦉',
        'celo': '🌿',
        'astar': '⭐',
        'metis': '🌌',
        'degen': '🎩',
        'opbnb': '🟨'
    }
    
    return chain_emojis.get(chain_name.lower(), '⛓️')

def format_alert_summary(alerts):
    """Indonesia: Format ringkasan alert untuk ditampilkan"""
    if not alerts:
        return "Tidak ada alert aktif"
    
    summary = f"{len(alerts)} alert aktif:\n"
    
    # Indonesia: Group by alert type
    above_count = len([a for a in alerts if a['alert_type'] == 'above'])
    below_count = len([a for a in alerts if a['alert_type'] == 'below'])
    percent_count = len([a for a in alerts if a['alert_type'] == 'percent'])
    
    if above_count > 0:
        summary += f"📈 {above_count} alert naik\n"
    if below_count > 0:
        summary += f"📉 {below_count} alert turun\n"
    if percent_count > 0:
        summary += f"📊 {percent_count} alert perubahan %\n"
    
    return summary.strip()

def create_quick_alert_keyboard(popular_tokens):
    """Indonesia: Buat keyboard untuk quick alert setup"""
    keyboard = []
    
    for token in popular_tokens[:6]:  # Indonesia: Max 6 token populer
        keyboard.append([InlineKeyboardButton(
            f"🚨 Alert {token['symbol']}", 
            callback_data=f"quick_alert_{token['address']}"
        )])
    
    keyboard.append([InlineKeyboardButton("➕ Alert Custom", callback_data='create_new_alert')])
    keyboard.append([InlineKeyboardButton("⬅️ Kembali", callback_data='main_menu')])
    
    return InlineKeyboardMarkup(keyboard)

def validate_ethereum_address(address):
    """Indonesia: Validasi format alamat Ethereum"""
    if not address:
        return False
    
    # Indonesia: Harus dimulai dengan 0x dan panjang 42 karakter
    if not address.startswith('0x') or len(address) != 42:
        return False
    
    # Indonesia: Harus berisi karakter hex yang valid
    try:
        int(address[2:], 16)
        return True
    except ValueError:
        return False

def truncate_address(address, start_chars=6, end_chars=4):
    """Indonesia: Potong alamat untuk tampilan yang lebih bersih"""
    if not address or len(address) < start_chars + end_chars:
        return address
    
    return f"{address[:start_chars]}...{address[-end_chars:]}"

def get_explorer_link(chain, address, tx_hash=None):
    """Indonesia: Dapatkan link explorer untuk alamat atau transaksi"""
    chain_data = CHAIN_CONFIG.get(chain.lower(), {})
    explorer_url = chain_data.get('explorer_url')
    
    if not explorer_url:
        return None
    
    if tx_hash:
        return f"{explorer_url}/tx/{tx_hash}"
    else:
        return f"{explorer_url}/address/{address}"

def format_large_number(number):
    """Indonesia: Format angka besar dengan K, M, B"""
    if number >= 1_000_000_000:
        return f"{number / 1_000_000_000:.2f}B"
    elif number >= 1_000_000:
        return f"{number / 1_000_000:.2f}M"
    elif number >= 1_000:
        return f"{number / 1_000:.2f}K"
    else:
        return f"{number:.2f}"
