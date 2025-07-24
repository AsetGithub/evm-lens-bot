# monitor.py (Versi Final dengan Pengecekan Settings)

import time
import logging
import requests
import threading
import asyncio
from telegram import Bot

import config
import database
from image_generator import create_transaction_image

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
bot = Bot(token=config.TELEGRAM_TOKEN)

CHAIN_CONFIG = {
    # ... (Isi CHAIN_CONFIG lengkap Anda di sini, tidak diringkas) ...
}

def make_rpc_request(rpc_url, method, params):
    # ... (Fungsi ini tidak berubah) ...

def get_price(coingecko_id):
    # ... (Fungsi ini tidak berubah) ...

async def send_photo_async(user_id, image_buffer, caption):
    # ... (Fungsi ini tidak berubah) ...

def process_and_send(tx, chain_name, chain_data, triggered_address):
    is_outgoing = triggered_address.lower() == tx['from'].lower()
    
    symbol = tx.get('asset')
    value = tx.get('value')
    is_airdrop = False # Defaultnya bukan airdrop
    
    if symbol is None:
        symbol = chain_data.get('symbol', 'Token')
        value = int(tx.get('rawContract', {}).get('value', '0x0'), 16) / 1e18
    elif value is not None and value == 0:
        is_airdrop = True
    elif value is None: # Kasus transfer NFT (ERC721 tidak punya 'value')
        is_airdrop = True

    coingecko_id = None
    if symbol == chain_data.get('symbol'):
        coingecko_id = chain_data.get('coingecko_id')

    price_usd = get_price(coingecko_id) if coingecko_id and value is not None else None
    value_usd = (value * price_usd) if price_usd and value is not None else 0
    value_usd_text = f" (~${value_usd:,.2f} USD)" if value_usd > 0 else ""
    amount_text = f"{value:.6f} {symbol}{value_usd_text}" if value is not None else "NFT Transfer"

    tx_data = {
        'chain': chain_name, 'direction': "➡️ KELUAR" if is_outgoing else "✅ MASUK",
        'color': '#F38BA8' if is_outgoing else '#A6E3A1',
        'from_addr': f"{tx['from'][:8]}...{tx['from'][-6:]}",
        'to_addr': f"{tx['to'][:8]}...{tx['to'][-6:]}",
        'tx_hash': tx['hash'], 'explorer_url': chain_data['explorer_url'],
        'amount_text': amount_text
    }

    image_buffer = create_transaction_image(tx_data)
    if image_buffer:
        caption = f"Transaksi terdeteksi untuk wallet <code>{triggered_address}</code>"
        users_to_notify = database.get_users_for_wallet(triggered_address, chain_name)
        
        for user_id in users_to_notify:
            settings = database.get_user_settings(user_id)
            # Cek filter
            if value_usd < settings['min_value_usd']:
                logging.info(f"Notifikasi untuk user {user_id} dilewati (di bawah nilai minimum).")
                continue
            if is_airdrop and not settings['notify_on_airdrop']:
                logging.info(f"Notifikasi untuk user {user_id} dilewati (airdrop dinonaktifkan).")
                continue
            
            asyncio.run(send_photo_async(user_id, image_buffer, caption))

def monitor_chain(chain_name, chain_data):
    # ... (Fungsi ini tidak berubah) ...

def main():
    # ... (Fungsi ini tidak berubah) ...

if __name__ == "__main__":
    main()
