import asyncio
import json
import logging
from telegram import Bot
import websockets

import config
import database

# Setup logging untuk melihat aktivitas di terminal
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Inisialisasi bot di sini khusus untuk mengirim notifikasi
bot = Bot(token=config.TELEGRAM_TOKEN)

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
    wallets_to_monitor = database.get_all_wallets_by_chain(chain_name)

    if not wallets_to_monitor:
        logging.info(f"[{chain_name}] Tidak ada wallet untuk dipantau. Cek lagi nanti.")
        return # Keluar jika tidak ada wallet di chain ini

    logging.info(f"[{chain_name}] Memantau {len(wallets_to_monitor)} wallet...")

    subscribe_request = {
        "jsonrpc": "2.0", "id": 1, "method": "alchemy_subscribe",
        "params": ["alchemy_pendingTransactions", {"toAddress": wallets_to_monitor, "fromAddress": wallets_to_monitor}]
    }

    async with websockets.connect(config.ALCHEMY_WSS_URL) as websocket:
        await websocket.send(json.dumps(subscribe_request))

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

async def main_loop():
    """Loop utama yang akan menjalankan monitor untuk setiap chain."""
    logging.info("Memulai Monitor...")
    # Untuk sekarang kita pantau WorldChain (karena API key Anda untuk itu)
    # Di masa depan, kita bisa buat ini dinamis
    while True:
        try:
            # URL Explorer untuk WorldChain belum ada, kita gunakan placeholder
            await monitor_chain("worldchain", "https://etherscan.io")
        except Exception as e:
            logging.error(f"Error Kritis di Monitor: {e}. Restart dalam 15 detik...")
            await asyncio.sleep(15)

if __name__ == "__main__":
    asyncio.run(main_loop())