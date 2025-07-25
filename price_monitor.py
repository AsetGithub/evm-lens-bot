# price_monitor.py
# Indonesia: Worker untuk monitor harga dan trigger alert

import asyncio
import time
import logging
from datetime import datetime
from telegram import Bot
import requests

import config
import database
from constants import CHAIN_CONFIG
from bot.utils import get_price

# Indonesia: Setup logging untuk monitor harga
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

bot = Bot(token=config.TELEGRAM_TOKEN)

class PriceMonitor:
    def __init__(self):
        self.price_cache = {}  # Indonesia: Cache harga untuk menghindari spam API
        self.last_check_time = {}
        self.coingecko_rate_limit = 0
        
    async def start_monitoring(self):
        """Indonesia: Mulai monitoring harga untuk semua alert aktif"""
        logging.info("🚀 Indonesia: Memulai Price Monitor untuk alert sistem...")
        
        while True:
            try:
                # Indonesia: Ambil semua alert aktif
                active_alerts = database.get_all_active_alerts()
                logging.info(f"📊 Indonesia: Monitoring {len(active_alerts)} alert aktif")
                
                if not active_alerts:
                    logging.info("😴 Indonesia: Tidak ada alert aktif, tidur 60 detik...")
                    await asyncio.sleep(60)
                    continue
                
                # Indonesia: Group alerts by token untuk efisiensi API calls
                alerts_by_token = self.group_alerts_by_token(active_alerts)
                
                # Indonesia: Check harga untuk setiap token
                for token_key, alerts in alerts_by_token.items():
                    await self.check_token_alerts(token_key, alerts)
                    
                    # Indonesia: Rate limiting untuk API calls
                    await asyncio.sleep(2)
                
                # Indonesia: Tunggu 30 detik sebelum check lagi
                logging.info("⏳ Indonesia: Menunggu 30 detik untuk check berikutnya...")
                await asyncio.sleep(30)
                
            except Exception as e:
                logging.error(f"❌ Indonesia: Error dalam price monitoring: {e}")
                await asyncio.sleep(60)
    
    def group_alerts_by_token(self, alerts):
        """Indonesia: Group alerts berdasarkan token untuk efisiensi"""
        grouped = {}
        for alert in alerts:
            token_key = f"{alert['chain']}_{alert['token_address']}"
            if token_key not in grouped:
                grouped[token_key] = []
            grouped[token_key].append(alert)
        return grouped
    
    async def check_token_alerts(self, token_key, alerts):
        """Indonesia: Check harga token dan trigger alert jika kondisi terpenuhi"""
        try:
            chain, token_address = token_key.split('_', 1)
            
            # Indonesia: Ambil harga saat ini
            current_price = await self.get_current_price(chain, token_address)
            
            if current_price is None:
                logging.warning(f"⚠️ Indonesia: Gagal mendapat harga untuk {token_key}")
                return
            
            # Indonesia: Check setiap alert untuk token ini
            for alert in alerts:
                if self.should_trigger_alert(alert, current_price):
                    await self.trigger_alert(alert, current_price)
                    
        except Exception as e:
            logging.error(f"❌ Indonesia: Error checking {token_key}: {e}")
    
    async def get_current_price(self, chain, token_address):
        """Indonesia: Ambil harga token saat ini dari berbagai sumber"""
        try:
            # Indonesia: Cek cache dulu (untuk menghindari rate limit)
            cache_key = f"{chain}_{token_address}"
            now = time.time()
            
            if cache_key in self.price_cache:
                cached_price, cached_time = self.price_cache[cache_key]
                if now - cached_time < 60:  # Indonesia: Cache 1 menit
                    return cached_price
            
            # Indonesia: Prioritas: Native token dulu (ETH, MATIC, dll)
            if self.is_native_token(chain, token_address):
                price = await self.get_native_token_price(chain)
            else:
                # Indonesia: Token custom, coba dari DEX atau CoinGecko
                price = await self.get_token_price_from_dex(chain, token_address)
                if price is None:
                    price = await self.get_token_price_from_coingecko(token_address)
            
            # Indonesia: Simpan ke cache
            if price is not None:
                self.price_cache[cache_key] = (price, now)
                
            return price
            
        except Exception as e:
            logging.error(f"❌ Indonesia: Error mendapat harga {chain}_{token_address}: {e}")
            return None
    
    def is_native_token(self, chain, token_address):
        """Indonesia: Check apakah ini native token (ETH, MATIC, dll)"""
        native_addresses = {
            'ethereum': ['0x0000000000000000000000000000000000000000', 
                        '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'],  # ETH & WETH
            'polygon': ['0x0000000000000000000000000000000000001010'],  # MATIC
            'arbitrum': ['0x0000000000000000000000000000000000000000'],  # ETH
            'optimism': ['0x0000000000000000000000000000000000000000'],  # ETH
        }
        
        return token_address.lower() in [addr.lower() for addr in native_addresses.get(chain, [])]
    
    async def get_native_token_price(self, chain):
        """Indonesia: Ambil harga native token dari CoinGecko"""
        chain_data = CHAIN_CONFIG.get(chain, {})
        coingecko_id = chain_data.get('coingecko_id')
        
        if coingecko_id:
            return get_price(coingecko_id)
        return None
    
    async def get_token_price_from_dex(self, chain, token_address):
        """Indonesia: Ambil harga token dari DEX (Uniswap, dll) via Alchemy"""
        try:
            # Indonesia: Untuk implementasi lengkap, bisa pakai Alchemy DEX APIs
            # Sementara return None, nanti implement sesuai kebutuhan
            return None
            
        except Exception as e:
            logging.error(f"❌ Indonesia: Error DEX price {token_address}: {e}")
            return None
    
    async def get_token_price_from_coingecko(self, token_address):
        """Indonesia: Coba ambil harga dari CoinGecko by contract address"""
        try:
            # Indonesia: Rate limiting untuk CoinGecko (max 10-50 calls per minute)
            now = time.time()
            if now - self.coingecko_rate_limit < 6:  # Indonesia: 6 detik antar call
                await asyncio.sleep(6)
            
            url = f"https://api.coingecko.com/api/v3/simple/token_price/ethereum"
            params = {
                'contract_addresses': token_address,
                'vs_currencies': 'usd'
            }
            
            response = requests.get(url, params=params, timeout=10)
            self.coingecko_rate_limit = time.time()
            
            if response.status_code == 200:
                data = response.json()
                return data.get(token_address.lower(), {}).get('usd')
            
            return None
            
        except Exception as e:
            logging.error(f"❌ Indonesia: Error CoinGecko price {token_address}: {e}")
            return None
    
    def should_trigger_alert(self, alert, current_price):
        """Indonesia: Cek apakah alert harus di-trigger"""
        alert_type = alert['alert_type']
        
        if alert_type == 'above':
            return current_price >= alert['target_price']
        elif alert_type == 'below':
            return current_price <= alert['target_price']
        elif alert_type == 'percent':
            created_price = alert.get('created_price', 0)
            if created_price <= 0:
                return False
            
            price_change_percent = ((current_price - created_price) / created_price) * 100
            target_percent = alert['target_percentage']
            
            # Indonesia: Check apakah perubahan sudah mencapai target
            if target_percent > 0:  # Indonesia: Alert untuk kenaikan
                return price_change_percent >= target_percent
            else:  # Indonesia: Alert untuk penurunan
                return price_change_percent <= target_percent
        
        return False
    
    async def trigger_alert(self, alert, current_price):
        """Indonesia: Trigger alert dan kirim notifikasi ke user"""
        try:
            # Indonesia: Mark alert sebagai triggered di database
            success = database.trigger_price_alert(alert['id'], current_price)
            
            if not success:
                logging.error(f"❌ Indonesia: Gagal update alert {alert['id']} di database")
                return
            
            # Indonesia: Buat pesan notifikasi
            message = self.create_alert_message(alert, current_price)
            
            # Indonesia: Kirim notifikasi ke user
            await bot.send_message(
                chat_id=alert['user_id'],
                text=message,
                parse_mode='Markdown'
            )
            
            # Indonesia: Log notifikasi ke database
            database.log_alert_notification(
                alert['id'], 
                alert['user_id'], 
                'price_reached', 
                message
            )
            
            logging.info(f"✅ Indonesia: Alert #{alert['id']} berhasil di-trigger untuk user {alert['user_id']}")
            
        except Exception as e:
            logging.error(f"❌ Indonesia: Error trigger alert {alert['id']}: {e}")
    
    def create_alert_message(self, alert, current_price):
        """Indonesia: Buat pesan notifikasi alert yang menarik"""
        symbol = alert['token_symbol']
        chain = alert['chain'].title()
        alert_type = alert['alert_type']
        
        # Indonesia: Emoji berdasarkan jenis alert
        if alert_type == 'above':
            emoji = "📈🚀"
            condition_text = f"naik di atas ${alert['target_price']:,.6f}"
        elif alert_type == 'below':
            emoji = "📉⚠️"
            condition_text = f"turun di bawah ${alert['target_price']:,.6f}"
        else:  # percent
            if alert['target_percentage'] > 0:
                emoji = "📈🎉"
                condition_text = f"naik {alert['target_percentage']:+.1f}%"
            else:
                emoji = "📉🔔"
                condition_text = f"turun {alert['target_percentage']:.1f}%"
        
        message = (
            f"{emoji} **ALERT HARGA TERCAPAI!**\n\n"
            f"🪙 **{symbol}** di jaringan **{chain}**\n"
            f"💰 **Harga Saat Ini:** ${current_price:,.6f}\n"
            f"🎯 **Kondisi:** {condition_text}\n\n"
            f"⏰ **Waktu:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n"
            f"🔔 Alert ini telah dinonaktifkan otomatis.\n"
            f"💡 Gunakan /alerts untuk membuat alert baru!"
        )
        
        return message

async def main():
    """Indonesia: Fungsi utama untuk menjalankan price monitor"""
    logging.info("🇮🇩 Indonesia: Memulai Price Monitor untuk EVM Lens Bot...")
    
    # Indonesia: Setup database enhanced
    database.setup_enhanced_database()
    
    # Indonesia: Buat instance monitor dan mulai
    monitor = PriceMonitor()
    await monitor.start_monitoring()

if __name__ == "__main__":
    asyncio.run(main())
