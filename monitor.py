import asyncio
import json
import logging
from telegram import Bot
import websockets
import requests

import config
import database
from image_generator import create_transaction_image

# Setup logging untuk melihat aktivitas di terminal
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
bot = Bot(token=config.TELEGRAM_TOKEN)

# Kamus konfigurasi final dengan semua jaringan yang didukung + data harga
CHAIN_CONFIG = {
    # == Top Tier & L2s Utama ==
    'ethereum': {'explorer_url': 'https://etherscan.io', 'wss_subdomain': 'eth-mainnet', 'coingecko_id': 'ethereum', 'symbol': 'ETH'},
    'arbitrum': {'explorer_url': 'https://arbiscan.io', 'wss_subdomain': 'arb-mainnet', 'coingecko_id': 'ethereum', 'symbol': 'ETH'},
    'optimism': {'explorer_url': 'https://optimistic.etherscan.io', 'wss_subdomain': 'opt-mainnet', 'coingecko_id': 'ethereum', 'symbol': 'ETH'},
    'base': {'explorer_url': 'https://basescan.org', 'wss_subdomain': 'base-mainnet', 'coingecko_id': 'ethereum', 'symbol': 'ETH'},
    'zksync': {'explorer_url': 'https://explorer.zksync.io', 'wss_subdomain': 'zksync-mainnet', 'coingecko_id': 'ethereum', 'symbol': 'ETH'},
    'linea': {'explorer_url': 'https://lineascan.build', 'wss_subdomain': 'linea-mainnet', 'coingecko_id': 'ethereum', 'symbol': 'ETH'},
    'scroll': {'explorer_url': 'https://scrollscan.com', 'wss_subdomain': 'scroll-mainnet', 'coingecko_id': 'ethereum', 'symbol': 'ETH'},
    'blast': {'explorer_url': 'https://blastscan.io', 'wss_subdomain': 'blast-mainnet', 'coingecko_id': 'ethereum', 'symbol': 'ETH'},
    'zora': {'explorer_url': 'https://explorer.zora.energy', 'wss_subdomain': 'zora-mainnet', 'coingecko_id': 'ethereum', 'symbol': 'ETH'},
    
    # L1 & Sidechains dengan token native sendiri
    'polygon': {'explorer_url': 'https://polygonscan.com', 'wss_subdomain': 'polygon-mainnet', 'coingecko_id': 'matic-network', 'symbol': 'MATIC'},
    'bsc': {'explorer_url': 'https://bscscan.com', 'wss_subdomain': 'bsc-mainnet', 'coingecko_id': 'binancecoin', 'symbol': 'BNB'},
    'avalanche': {'explorer_url': 'https://snowtrace.io', 'wss_subdomain': 'avax-mainnet', 'coingecko_id': 'avalanche-2', 'symbol': 'AVAX'},
    'fantom': {'explorer_url': 'https://ftmscan.com', 'wss_subdomain': 'fantom-mainnet', 'coingecko_id': 'fantom', 'symbol': 'FTM'},
    'mantle': {'explorer_url': 'https://mantlescan.xyz', 'wss_subdomain': 'mantle-mainnet', 'coingecko_id': 'mantle', 'symbol': 'MNT'},
    'cronos': {'explorer_url': 'https://cronoscan.com', 'wss_subdomain': 'cronos-mainnet', 'coingecko_id': 'crypto-com-chain', 'symbol': 'CRO'},
    'gnosis': {'explorer_url': 'https://gnosisscan.io', 'wss_subdomain': 'gnosis-mainnet', 'coingecko_id': 'xdai', 'symbol': 'xDAI'},
    'celo': {'explorer_url': 'https://celoscan.io', 'wss_subdomain': 'celo-mainnet', 'coingecko_id': 'celo', 'symbol': 'CELO'},
    'astar': {'explorer_url': 'https://astar.subscan.io', 'wss_subdomain': 'astar-mainnet', 'coingecko_id': 'astar', 'symbol': 'ASTR'},
    'metis': {'explorer_url': 'https://andromeda-explorer.metis.io', 'wss_subdomain': 'metis-mainnet', 'coingecko_id': 'metis-token', 'symbol': 'METIS'},
    'degen': {'explorer_url': 'https://explorer.degen.tips', 'wss_subdomain': 'degen-mainnet', 'coingecko_id': 'degen-base', 'symbol': 'DEGEN'},
    'opbnb': {'explorer_url': 'https://opbnb.bscscan.com', 'wss_subdomain': 'opbnb-mainnet', 'coingecko_id': 'binancecoin', 'symbol': 'BNB'},
}

def get_price(coingecko_id):
    """Mengambil harga dari CoinGecko API."""
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coingecko_id}&vs_currencies=usd"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data[coingecko_id]['usd']
    except Exception as e:
        logging.error(f"Gagal mengambil harga untuk {coingecko_id}: {e}")
        return None

async def send_notification(user_ids, message):
    for user_id in user_ids:
        try:
            await bot.send_message(chat_id=user_id, text=message, parse_mode='HTML')
            logging.info(f"Notifikasi teks terkirim ke user {user_id}")
        except Exception as e:
            logging.error(f"Gagal mengirim notifikasi teks ke user {user_id}: {e}")

async def monitor_chain(chain_name, chain_data):
    wss_url = f"wss://{chain_data['wss_subdomain']}.g.alchemy.com/v2/{config.ALCHEMY_API_KEY}"
    explorer_url = chain_data['explorer_url']
    coingecko_id = chain_data.get('coingecko_id')
    symbol = chain_data.get('symbol', 'Token')
    
    while True:
        try:
            wallets_to_monitor = database.get_all_wallets_by_chain(chain_name)
            if not wallets_to_monitor:
                logging.info(f"[{chain_name}] Tidak ada wallet untuk dipantau. Cek lagi dalam 60 detik.")
                await asyncio.sleep(60)
                continue

            logging.info(f"[{chain_name}] Memantau {len(wallets_to_monitor)} wallet...")
            subscribe_request = {
                "jsonrpc": "2.0", "id": 1, "method": "alchemy_subscribe",
                "params": ["alchemy_minedTransactions", {"toAddress": wallets_to_monitor, "fromAddress": wallets_to_monitor}]
            }

            async with websockets.connect(wss_url) as websocket:
                await websocket.send(json.dumps(subscribe_request))
                logging.info(f"[{chain_name}] Berhasil terhubung ke WebSocket.")

                async for message in websocket:
                    data = json.loads(message)
                    logging.info(f"[{chain_name}] Menerima data dari WebSocket.")
                    
                    if 'params' not in data or 'result' not in data['params']:
                        continue
                    
                    tx = data['params']['result']
                    tx_hash, from_addr, to_addr = tx.get('hash'), tx.get('from'), tx.get('to')

                    if not all([tx_hash, from_addr, to_addr]):
                        continue

                    value_wei = int(tx.get('value', '0x0'), 16)
                    value_native = value_wei / 1e18

                    triggered_address = ""
                    if from_addr.lower() in wallets_to_monitor:
                        triggered_address = from_addr
                    elif to_addr.lower() in wallets_to_monitor:
                        triggered_address = to_addr
                    
                    if not triggered_address:
                        continue
                    
                    logging.info(f"[{chain_name}] Transaksi relevan terdeteksi: {tx_hash}")

                    is_outgoing = triggered_address.lower() == from_addr.lower()
                    
                    tx_data = {
                        'chain': chain_name,
                        'direction': "➡️ KELUAR" if is_outgoing else "✅ MASUK",
                        'color': '#F38BA8' if is_outgoing else '#A6E3A1',
                        'from_addr': f"{from_addr[:8]}...{from_addr[-6:]}",
                        'to_addr': f"{to_addr[:8]}...{to_addr[-6:]}",
                        'tx_hash': tx_hash,
                        'explorer_url': explorer_url
                    }
                    
                    if value_native > 0:
                        price_usd = get_price(coingecko_id) if coingecko_id else None
                        value_usd_text = ""
                        if price_usd:
                            value_usd = value_native * price_usd
                            value_usd_text = f" (~${value_usd:,.2f} USD)"
                        tx_data['amount_text'] = f"{value_native:.6f} {symbol}{value_usd_text}"
                    else:
                        if is_outgoing: continue
                        tx_data['amount_text'] = "Token / NFT Transfer"
                    
                    logging.info(f"[{chain_name}] Mempersiapkan data untuk membuat gambar.")
                    image_buffer = create_transaction_image(tx_data)

                    if image_buffer:
                        logging.info(f"[{chain_name}] Gambar berhasil dibuat. Mempersiapkan untuk mengirim...")
                        caption = f"Transaksi terdeteksi di jaringan {chain_name.title()} untuk wallet <code>{triggered_address}</code>"
                        users_to_notify = database.get_users_for_wallet(triggered_address, chain_name)
                        for user_id in users_to_notify:
                            try:
                                await bot.send_photo(chat_id=user_id, photo=image_buffer, caption=caption, parse_mode='HTML')
                                logging.info(f"Kuitansi gambar terkirim ke user {user_id}")
                                image_buffer.seek(0)
                            except Exception as e:
                                logging.error(f"Gagal mengirim foto ke user {user_id}: {e}")
                    else:
                        logging.warning(f"[{chain_name}] Gagal membuat gambar (image_buffer is None). Notifikasi tidak dikirim.")

        except Exception as e:
            logging.error(f"[{chain_name}] Error pada monitor: {e}. Mencoba koneksi ulang...")
            await asyncio.sleep(15)

async def main():
    """Fungsi utama yang menjalankan semua monitor."""
    logging.info("Memulai Mesin Pemantau (Versi Perbaikan Final)...")
    database.setup_database()
    active_chains = database.get_active_chains()
    tasks = []
    for chain in active_chains:
        if chain in CHAIN_CONFIG:
            task = asyncio.create_task(monitor_chain(chain, CHAIN_CONFIG[chain]))
            tasks.append(task)
            logging.info(f"Membuat tugas pemantauan untuk jaringan: {chain}")
        else:
            logging.warning(f"Konfigurasi untuk jaringan '{chain}' tidak ditemukan di CHAIN_CONFIG. Melewati.")
    
    if tasks:
        await asyncio.gather(*tasks)
    else:
        logging.info("Tidak ada jaringan aktif yang dikenali untuk dipantau saat ini.")

if __name__ == "__main__":
    asyncio.run(main())
