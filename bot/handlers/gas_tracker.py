# bot/handlers/gas_tracker.py

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
import config
from constants import CHAIN_CONFIG
from bot.utils import make_rpc_request, get_network_keyboard

async def gas_start(update: Update, context):
    """Memulai alur pengecekan gas, menampilkan pilihan jaringan."""
    text = "⛽ Pilih jaringan untuk memeriksa gas fee:"
    keyboard = get_network_keyboard('gas_')
    
    if update.callback_query:
        query = update.callback_query; await query.answer()
        await query.edit_message_text(text=text, reply_markup=keyboard)
    else: # Jika dari command /gas
        await update.message.reply_text(text=text, reply_markup=keyboard)

async def get_gas_price(update: Update, context):
    """Mengambil dan menampilkan harga gas untuk jaringan yang dipilih."""
    query = update.callback_query; await query.answer()
    chain = query.data.split('_')[1]
    
    await query.edit_message_text(f"⏳ Sedang memeriksa gas fee di jaringan {chain.title()}...")

    chain_data = CHAIN_CONFIG.get(chain, {})
    rpc_url = f"https://{chain_data['rpc_subdomain']}.g.alchemy.com/v2/{config.ALCHEMY_API_KEY}"
    
    response = make_rpc_request(rpc_url, "eth_gasPrice", [])
    
    if response and 'result' in response:
        gas_price_wei = int(response['result'], 16)
        gas_price_gwei = gas_price_wei / 1e9
        text = (
            f"⛽ **Gas Fee Saat Ini ({chain.title()})**\n\n"
            f"🔹 **{gas_price_gwei:.2f} Gwei**"
        )
    else:
        text = f"❌ Gagal mengambil data gas fee untuk jaringan {chain.title()}."

    keyboard = [
        [InlineKeyboardButton("🔎 Cek Jaringan Lain", callback_data='gas_start')],
        [InlineKeyboardButton("⬅️ Kembali ke Menu Utama", callback_data='main_menu')]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')