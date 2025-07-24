# monitor.py (Versi Final dengan Perbaikan Impor Melingkar)

import time
import logging
import requests
import threading
import asyncio
from telegram import Bot

import config
import database
from image_generator import create_transaction_image
from bot.utils import get_price, make_rpc_request
from constants import CHAIN_CONFIG # <-- PERUBAHAN PENTING

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
bot = Bot(token=config.TELEGRAM_TOKEN)

# (Sisa kode dari sini hingga akhir tidak berubah dari versi terakhir yang berfungsi)
async def send_photo_async(user_id, image_buffer, caption):
    try:
        await bot.send_photo(chat_id=user_id, photo=image_buffer, caption=caption, parse_mode='HTML')
        logging.info(f"Kuitansi gambar BERHASIL dikirim ke user {user_id}")
        image_buffer.seek(0)
    except Exception as e:
        logging.error(f"Gagal mengirim foto ke user {user_id}: {e}")

def process_and_send(tx, chain_name, chain_data, triggered_address):
    is_outgoing = triggered_address.lower() == tx['from'].lower()
    symbol = tx.get('asset')
    value = tx.get('value')
    is_airdrop = False
    
    if symbol is None:
        symbol = chain_data.get('symbol', 'Token')
        value = int(tx.get('rawContract', {}).get('value', '0x0'), 16) / 1e18
    elif value is not None and value == 0:
        is_airdrop = True
    elif value is None:
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
            if value_usd < settings['min_value_usd']:
                logging.info(f"Notifikasi untuk user {user_id} dilewati (di bawah nilai minimum).")
                continue
            if is_airdrop and not settings['notify_on_airdrop']:
                logging.info(f"Notifikasi untuk user {user_id} dilewati (airdrop dinonaktifkan).")
                continue
            
            asyncio.run(send_photo_async(user_id, image_buffer, caption))

def monitor_chain(chain_name, chain_data):
    rpc_url = f"https://{chain_data['rpc_subdomain']}.g.alchemy.com/v2/{config.ALCHEMY_API_KEY}"
    logging.info(f"[{chain_name}] Memulai pemantauan dengan metode `getAssetTransfers` ke {rpc_url}")
    last_processed_block = -1

    while True:
        try:
            wallets_to_monitor = database.get_all_wallets_by_chain(chain_name)
            if not wallets_to_monitor:
                time.sleep(60)
                continue

            latest_block_hex = make_rpc_request(rpc_url, "eth_blockNumber", []).get('result')
            if not latest_block_hex:
                time.sleep(15)
                continue
            
            latest_block = int(latest_block_hex, 16)

            if last_processed_block == -1:
                last_processed_block = latest_block

            to_block_to_check = latest_block - 2
            
            if to_block_to_check > last_processed_block:
                from_block_to_check = last_processed_block + 1
                logging.info(f"[{chain_name}] Memeriksa blok dari {hex(from_block_to_check)} hingga {hex(to_block_to_check)}")
                
                params = [{
                    "fromBlock": hex(from_block_to_check),
                    "toBlock": hex(to_block_to_check),
                    "address": wallets_to_monitor,
                    "category": ["external", "erc20", "erc721", "erc1155"],
                    "withMetadata": True,
                    "excludeZeroValue": False,
                }]
                
                response = make_rpc_request(rpc_url, "alchemy_getAssetTransfers", params)
                
                if response and 'result' in response and response['result'].get('transfers'):
                    for tx in response['result']['transfers']:
                        triggered_address = ""
                        if tx['from'].lower() in wallets_to_monitor:
                            triggered_address = tx['from']
                        elif tx['to'].lower() in wallets_to_monitor:
                            triggered_address = tx['to']
                        
                        if triggered_address:
                            process_and_send(tx, chain_name, chain_data, triggered_address)

                last_processed_block = to_block_to_check

            time.sleep(20)

        except Exception as e:
            logging.error(f"[{chain_name}] Error pada loop monitor: {e}")
            time.sleep(30)

def start_monitoring():
    """Fungsi utama yang menjalankan semua monitor dalam thread terpisah."""
    logging.info("Memulai Mesin Pemantau (Versi Final)...")
    database.setup_database()
    
    threads = []
    active_chains = database.get_active_chains()
    for chain in active_chains:
        if chain in CHAIN_CONFIG:
            thread = threading.Thread(target=monitor_chain, args=(chain, CHAIN_CONFIG[chain]))
            threads.append(thread)
            thread.start()
            logging.info(f"Thread pemantauan untuk jaringan '{chain}' telah dimulai.")
        else:
            logging.warning(f"Konfigurasi untuk jaringan '{chain}' tidak ditemukan. Melewati.")
            
    for thread in threads:
        thread.join()

if __name__ == "__main__":
    start_monitoring()
