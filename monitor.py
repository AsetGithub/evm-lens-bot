# monitor.py (Versi Final dengan perbaikan alchemy_getAssetTransfers)

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
    # == Top Tier & L2s Utama ==
    'ethereum': {'explorer_url': 'https://etherscan.io', 'rpc_subdomain': 'eth-mainnet', 'coingecko_id': 'ethereum', 'symbol': 'ETH'},
    'arbitrum': {'explorer_url': 'https://arbiscan.io', 'rpc_subdomain': 'arb-mainnet', 'coingecko_id': 'ethereum', 'symbol': 'ETH'},
    'optimism': {'explorer_url': 'https://optimistic.etherscan.io', 'rpc_subdomain': 'opt-mainnet', 'coingecko_id': 'ethereum', 'symbol': 'ETH'},
    'base': {'explorer_url': 'https://basescan.org', 'rpc_subdomain': 'base-mainnet', 'coingecko_id': 'ethereum', 'symbol': 'ETH'},
    'zksync': {'explorer_url': 'https://explorer.zksync.io', 'rpc_subdomain': 'zksync-mainnet', 'coingecko_id': 'ethereum', 'symbol': 'ETH'},
    'linea': {'explorer_url': 'https://lineascan.build', 'rpc_subdomain': 'linea-mainnet', 'coingecko_id': 'ethereum', 'symbol': 'ETH'},
    'scroll': {'explorer_url': 'https://scrollscan.com', 'rpc_subdomain': 'scroll-mainnet', 'coingecko_id': 'ethereum', 'symbol': 'ETH'},
    'blast': {'explorer_url': 'https://blastscan.io', 'rpc_subdomain': 'blast-mainnet', 'coingecko_id': 'ethereum', 'symbol': 'ETH'},
    'zora': {'explorer_url': 'https://explorer.zora.energy', 'rpc_subdomain': 'zora-mainnet', 'coingecko_id': 'ethereum', 'symbol': 'ETH'},
    
    # L1 & Sidechains dengan token native sendiri
    'polygon': {'explorer_url': 'https://polygonscan.com', 'rpc_subdomain': 'polygon-mainnet', 'coingecko_id': 'matic-network', 'symbol': 'MATIC'},
    'bsc': {'explorer_url': 'https://bscscan.com', 'rpc_subdomain': 'bsc-mainnet', 'coingecko_id': 'binancecoin', 'symbol': 'BNB'},
    'avalanche': {'explorer_url': 'https://snowtrace.io', 'rpc_subdomain': 'avax-mainnet', 'coingecko_id': 'avalanche-2', 'symbol': 'AVAX'},
    'fantom': {'explorer_url': 'https://ftmscan.com', 'rpc_subdomain': 'fantom-mainnet', 'coingecko_id': 'fantom', 'symbol': 'FTM'},
    'mantle': {'explorer_url': 'https://mantlescan.xyz', 'rpc_subdomain': 'mantle-mainnet', 'coingecko_id': 'mantle', 'symbol': 'MNT'},
    'cronos': {'explorer_url': 'https://cronoscan.com', 'rpc_subdomain': 'cronos-mainnet', 'coingecko_id': 'crypto-com-chain', 'symbol': 'CRO'},
    'gnosis': {'explorer_url': 'https://gnosisscan.io', 'rpc_subdomain': 'gnosis-mainnet', 'coingecko_id': 'xdai', 'symbol': 'xDAI'},
    'celo': {'explorer_url': 'https://celoscan.io', 'rpc_subdomain': 'celo-mainnet', 'coingecko_id': 'celo', 'symbol': 'CELO'},
    'astar': {'explorer_url': 'https://astar.subscan.io', 'rpc_subdomain': 'astar-mainnet', 'coingecko_id': 'astar', 'symbol': 'ASTR'},
    'metis': {'explorer_url': 'https://andromeda-explorer.metis.io', 'rpc_subdomain': 'metis-mainnet', 'coingecko_id': 'metis-token', 'symbol': 'METIS'},
    'degen': {'explorer_url': 'https://explorer.degen.tips', 'rpc_subdomain': 'degen-mainnet', 'coingecko_id': 'degen-base', 'symbol': 'DEGEN'},
    'opbnb': {'explorer_url': 'https://opbnb.bscscan.com', 'rpc_subdomain': 'opbnb-mainnet', 'coingecko_id': 'binancecoin', 'symbol': 'BNB'},
}

def make_rpc_request(rpc_url, method, params):
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    try:
        response = requests.post(rpc_url, json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logging.error(f"Error saat melakukan request ke RPC: {e}")
    return None

def get_price(coingecko_id):
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coingecko_id}&vs_currencies=usd"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data.get(coingecko_id, {}).get('usd')
    except Exception as e:
        logging.error(f"Gagal mengambil harga untuk {coingecko_id}: {e}")
    return None

async def send_photo_async(user_id, image_buffer, caption):
    """Fungsi async wrapper untuk send_photo agar tidak ada warning."""
    try:
        await bot.send_photo(chat_id=user_id, photo=image_buffer, caption=caption, parse_mode='HTML')
        logging.info(f"Kuitansi gambar BERHASIL dikirim ke user {user_id}")
        image_buffer.seek(0)
    except Exception as e:
        logging.error(f"Gagal mengirim foto ke user {user_id}: {e}")

def process_and_send(tx, chain_name, chain_data, triggered_address):
    """Memproses data transaksi yang sudah pasti relevan dan mengirim notifikasi."""
    is_outgoing = triggered_address.lower() == tx['from'].lower()
    
    symbol = tx.get('asset')
    value = tx.get('value')
    if symbol is None:
        symbol = chain_data.get('symbol', 'Token')
        value = int(tx.get('rawContract', {}).get('value', '0x0'), 16) / 1e18

    coingecko_id = None
    if symbol == chain_data.get('symbol'):
        coingecko_id = chain_data.get('coingecko_id')

    price_usd = get_price(coingecko_id) if coingecko_id and value is not None else None
    value_usd_text = f" (~${(value * price_usd):,.2f} USD)" if price_usd and value is not None else ""
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
        caption = f"Transaksi terdeteksi di jaringan {chain_name.title()} untuk wallet <code>{triggered_address}</code>"
        users_to_notify = database.get_users_for_wallet(triggered_address, chain_name)
        for user_id in users_to_notify:
            asyncio.run(send_photo_async(user_id, image_buffer, caption))

def monitor_chain(chain_name, chain_data):
    """Fungsi utama untuk memantau satu jaringan dengan metode polling `getAssetTransfers`."""
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

            if latest_block > last_processed_block:
                logging.info(f"[{chain_name}] Memeriksa blok dari {hex(last_processed_block + 1)} hingga {hex(latest_block)}")
                
                params = [{
                    "fromBlock": hex(last_processed_block + 1),
                    "toBlock": hex(latest_block),
                    "address": wallets_to_monitor,
                    "category": ["external", "internal", "erc20", "erc721", "erc1155"],
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

                last_processed_block = latest_block

            time.sleep(15)

        except Exception as e:
            logging.error(f"[{chain_name}] Error pada loop monitor: {e}")
            time.sleep(30)

def main():
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
    main()
