# bot/utils.py - V2 Complete dengan Price Alert System
# Indonesia: Utility functions dengan tambahan untuk price alerts

import requests
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from constants import CHAIN_CONFIG

def make_rpc_request(rpc_url, method, params):
    """Indonesia: Fungsi pembantu untuk membuat permintaan JSON-RPC."""
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    try:
        response = requests.post(rpc_url, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logging.error(f"Error saat melakukan request ke RPC: {e}")
    return None

def get_price(coingecko_id):
    """Indonesia: Mengambil harga dari CoinGecko API."""
    if not coingecko_id: 
        return None
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coingecko_id}&vs_currencies=usd"
        response = requests.get(url, timeout=10)
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
            InlineKeyboardButton("🚨 Price Alerts", callback_data='alert_menu'),
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

def format_time_ago(timestamp):
    """Indonesia: Format waktu relatif (misalnya '2 jam yang lalu')"""
    import datetime
    try:
        if isinstance(timestamp, str):
            dt = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        else:
            dt = timestamp
        
        now = datetime.datetime.now(datetime.timezone.utc)
        diff = now - dt.replace(tzinfo=datetime.timezone.utc)
        
        if diff.days > 0:
            return f"{diff.days} hari lalu"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} jam lalu"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} menit lalu"
        else:
            return "Baru saja"
    except:
        return "Tidak diketahui"

def create_price_alert_keyboard(current_price, symbol):
    """Indonesia: Buat keyboard untuk setup alert cepat berdasarkan harga current"""
    keyboard = []
    
    # Indonesia: Preset alert berdasarkan harga saat ini
    if current_price:
        # Alert naik 10%, 25%, 50%
        keyboard.append([
            InlineKeyboardButton(f"📈 +10% (${current_price * 1.1:.4f})", 
                               callback_data=f"quick_alert_above_{current_price * 1.1:.6f}"),
            InlineKeyboardButton(f"📈 +25% (${current_price * 1.25:.4f})", 
                               callback_data=f"quick_alert_above_{current_price * 1.25:.6f}")
        ])
        
        # Alert turun 10%, 25%
        keyboard.append([
            InlineKeyboardButton(f"📉 -10% (${current_price * 0.9:.4f})", 
                               callback_data=f"quick_alert_below_{current_price * 0.9:.6f}"),
            InlineKeyboardButton(f"📉 -25% (${current_price * 0.75:.4f})", 
                               callback_data=f"quick_alert_below_{current_price * 0.75:.6f}")
        ])
    
    # Manual setup
    keyboard.append([InlineKeyboardButton("⚙️ Setup Manual", callback_data='create_new_alert')])
    keyboard.append([InlineKeyboardButton("⬅️ Kembali", callback_data='alert_menu')])
    
    return InlineKeyboardMarkup(keyboard)

def get_popular_crypto_list():
    """Indonesia: Daftar cryptocurrency populer untuk alert"""
    return [
        {'symbol': 'BTC', 'name': 'Bitcoin', 'coingecko_id': 'bitcoin'},
        {'symbol': 'ETH', 'name': 'Ethereum', 'coingecko_id': 'ethereum'},
        {'symbol': 'BNB', 'name': 'BNB', 'coingecko_id': 'binancecoin'},
        {'symbol': 'MATIC', 'name': 'Polygon', 'coingecko_id': 'matic-network'},
        {'symbol': 'ARB', 'name': 'Arbitrum', 'coingecko_id': 'arbitrum'},
        {'symbol': 'OP', 'name': 'Optimism', 'coingecko_id': 'optimism'},
    ]

def create_notification_preview(alert_data, current_price):
    """Indonesia: Buat preview notifikasi alert"""
    symbol = alert_data['token_symbol']
    alert_type = alert_data['alert_type']
    
    if alert_type == 'above':
        emoji = "📈🚀"
        condition = f"naik di atas ${alert_data['target_price']:,.6f}"
    elif alert_type == 'below':
        emoji = "📉⚠️"
        condition = f"turun di bawah ${alert_data['target_price']:,.6f}"
    else:  # percent
        emoji = "📊🔔"
        condition = f"berubah {alert_data['target_percentage']:+.1f}%"
    
    preview = (
        f"🔔 **Preview Notifikasi:**\n\n"
        f"{emoji} **ALERT HARGA TERCAPAI!**\n\n"
        f"🪙 **{symbol}** \n"
        f"💰 **Harga:** ${current_price:,.6f}\n"
        f"🎯 **Kondisi:** {condition}\n"
        f"⏰ **Waktu:** [Saat alert tercapai]\n\n"
        f"*Ini adalah preview. Notifikasi akan dikirim saat kondisi terpenuhi.*"
    )
    
    return preview
