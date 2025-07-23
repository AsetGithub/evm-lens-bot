import asyncio
import json
import logging
from telegram import Bot
import websockets

import config
import database

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Inisialisasi bot untuk mengirim notifikasi
bot = Bot(token=config.TELEGRAM_TOKEN)

# Konfigurasi untuk setiap jaringan
# Kamus konfigurasi final dengan semua jaringan yang didukung
CHAIN_CONFIG = {
    # == Top Tier & L2s Utama ==
    'ethereum': {'explorer_url': 'https://etherscan.io', 'wss_subdomain': 'eth-mainnet'},
    'polygon': {'explorer_url': 'https://polygonscan.com', 'wss_subdomain': 'polygon-mainnet'},
    'bsc': {'explorer_url': 'https://bscscan.com', 'wss_subdomain': 'bsc-mainnet'},
    'arbitrum': {'explorer_url': 'https://arbiscan.io', 'wss_subdomain': 'arb-mainnet'},
    'optimism': {'explorer_url': 'https://optimistic.etherscan.io', 'wss_subdomain': 'opt-mainnet'},
    'base': {'explorer_url': 'https://basescan.org', 'wss_subdomain': 'base-mainnet'},
    'avalanche': {'explorer_url': 'https://snowtrace.io', 'wss_subdomain': 'avax-mainnet'},
    'zksync': {'explorer_url': 'https://explorer.zksync.io', 'wss_subdomain': 'zksync-mainnet'},
    'linea': {'explorer_url': 'https://lineascan.build', 'wss_subdomain': 'linea-mainnet'},
    'scroll': {'explorer_url': 'https://scrollscan.com', 'wss_subdomain': 'scroll-mainnet'},
    'blast': {'explorer_url': 'https://blastscan.io', 'wss_subdomain': 'blast-mainnet'},
    'mantle': {'explorer_url': 'https://mantlescan.xyz', 'wss_subdomain': 'mantle-mainnet'},

    # == L1 Populer Lainnya ==
    'fantom': {'explorer_url': 'https://ftmscan.com', 'wss_subdomain': 'fantom-mainnet'},
    'cronos': {'explorer_url': 'https://cronoscan.com', 'wss_subdomain': 'cronos-mainnet'},
    'gnosis': {'explorer_url': 'https://gnosisscan.io', 'wss_subdomain': 'gnosis-mainnet'},
    'celo': {'explorer_url': 'https://celoscan.io', 'wss_subdomain': 'celo-mainnet'},
    'astar': {'explorer_url': 'https://astar.subscan.io', 'wss_subdomain': 'astar-mainnet'},
    'metis': {'explorer_url': 'https://andromeda-explorer.metis.io', 'wss_subdomain': 'metis-mainnet'},
    
    # == Jaringan Spesifik Komunitas ==
    'degen': {'explorer_url': 'https://explorer.degen.tips', 'wss_subdomain': 'degen-mainnet'},
    'zora': {'explorer_url': 'https://explorer.zora.energy', 'wss_subdomain': 'zora-mainnet'},
    'opbnb': {'explorer_url': 'https://opbnb.bscscan.com', 'wss_subdomain': 'opbnb-mainnet'},
}

async def send_notification(user_ids, message):
    """Mengirim notifikasi ke semua user yang memantau wallet ini."""
    for user_id in user_ids:
        try:
            await bot.send_message(chat_id=user_id, text=message, parse_mode='HTML')
            logging.info(f"Notifikasi terkirim ke user {user_id}")
        except Exception as e:
            logging.error(f"Gagal mengirim notifikasi ke user {user_id}: {e}")

async def monitor_chain(chain_name, explorer_url):
    """Fungsi utama untuk memantau satu jaringan blockchain."""
    while True: # Loop selamanya untuk mencoba koneksi ulang jika gagal
        try:
            wallets_to_monitor = database.get_all_wallets_by_chain(chain_name)
            if not wallets_to_monitor:
                logging.info(f"[{chain_name}] Tidak ada wallet untuk dipantau. Cek lagi dalam 60 detik.")
                await asyncio.sleep(60)
                continue

            logging.info(f"[{chain_name}] Memantau {len(wallets_to_monitor)} wallet...")

            subscribe_request = {
                "jsonrpc": "2.0", "id": 1, "method": "alchemy_subscribe",
                "params": ["alchemy_pendingTransactions", {"toAddress": wallets_to_monitor, "fromAddress": wallets_to_monitor}]
            }

            async with websockets.connect(config.ALCHEMY_WSS_URL) as websocket:
                await websocket.send(json.dumps(subscribe_request))
                logging.info(f"[{chain_name}] Berhasil terhubung ke WebSocket dan berlangganan notifikasi.")

                async for message in websocket:
                    data = json.loads(message)
                    if 'params' not in data or 'result' not in data['params']: continue

                    tx = data['params']['result']
                    tx_hash, from_addr, to_addr = tx.get('hash'), tx.get('from'), tx.get('to')
                    value_wei = int(tx.get('value', '0x0'), 16)
                    value_eth = value_wei / 1e18

                    triggered_address = ""
                    if from_addr in wallets_to_monitor: triggered_address = from_addr
                    elif to_addr in wallets_to_monitor: triggered_address = to_addr
                    if not triggered_address: continue

                    direction = "➡️ KELUAR" if triggered_address == from_addr else "✅ MASUK"

                    notification_message = (
                        f"<b>🔔 Notifikasi Transaksi Baru ({chain_name.title()})</b>\n\n"
                        f"Wallet: <code>{triggered_address}</code>\n"
                        f"Tipe: {direction}\n"
                        f"Jumlah: {value_eth:.6f}\n"
                        f"Dari: <code>{from_addr}</code>\n"
                        f"Ke: <code>{to_addr}</code>\n\n"
                        f"<a href='{explorer_url}/tx/{tx_hash}'>Lihat di Explorer</a>"
                    )

                    users_to_notify = database.get_users_for_wallet(triggered_address, chain_name)
                    await send_notification(users_to_notify, notification_message)

        except Exception as e:
            logging.error(f"[{chain_name}] Error pada monitor: {e}. Mencoba koneksi ulang dalam 15 detik...")
            await asyncio.sleep(15)

async def main():
    """Fungsi utama yang menjalankan semua monitor."""
    logging.info("Memulai Mesin Pemantau Multi-Jaringan...")
    
    active_chains = database.get_active_chains()
    tasks = []
    for chain in active_chains:
        if chain in CHAIN_CONFIG:
            config = CHAIN_CONFIG[chain]
            task = asyncio.create_task(monitor_chain(chain, config['explorer_url']))
            tasks.append(task)
            logging.info(f"Membuat tugas pemantauan untuk jaringan: {chain}")
        else:
            logging.warning(f"Konfigurasi untuk jaringan '{chain}' tidak ditemukan. Melewati.")
    
    if tasks:
        await asyncio.gather(*tasks)
    else:
        logging.info("Tidak ada jaringan aktif untuk dipantau saat ini.")

if __name__ == "__main__":
    asyncio.run(main())
