# bot/handlers/price_alerts.py - VERSI LENGKAP DAN DIPERBAIKI

import logging
import random
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ConversationHandler, MessageHandler, filters
import database
import config  #<-- Pastikan config diimpor
from constants import CHAIN_CONFIG
from bot.utils import get_price, make_rpc_request, get_network_keyboard

# State untuk alur percakapan alert harga
PILIH_CHAIN_ALERT, PILIH_TOKEN_ALERT, SET_HARGA_TARGET, PILIH_JENIS_ALERT = range(10, 14)

async def alert_menu(update: Update, context):
    """Menu utama untuk sistem alert harga"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    active_alerts = database.get_user_active_alerts(user_id)
    
    text = (
        "🚨 **Sistem Alert Harga**\n\n"
        "Dapatkan notifikasi ketika harga token mencapai target yang Anda tentukan!\n\n"
        f"📊 Alert Aktif: **{len(active_alerts)}** alert\n\n"
        "Pilih menu di bawah:"
    )
    
    keyboard = [
        [InlineKeyboardButton("➕ Buat Alert Baru", callback_data='create_new_alert')],
        [InlineKeyboardButton("📋 Lihat Alert Aktif", callback_data='view_active_alerts')],
        [InlineKeyboardButton("📈 Alert Populer", callback_data='popular_alerts')],
        [InlineKeyboardButton("⬅️ Kembali ke Menu Utama", callback_data='main_menu')]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def create_alert_start(update: Update, context):
    """Memulai proses pembuatan alert baru"""
    query = update.callback_query
    await query.answer()
    
    text = "🌐 Pilih jaringan untuk token yang ingin di-alert:"
    keyboard = get_network_keyboard('alert_chain_')
    
    await query.edit_message_text(text=text, reply_markup=keyboard)
    return PILIH_CHAIN_ALERT

async def select_alert_chain(update: Update, context):
    """User memilih chain untuk alert"""
    query = update.callback_query
    await query.answer()
    
    chain = query.data.split('_')[2]
    context.user_data['alert_chain'] = chain
    
    popular_tokens = get_popular_tokens_for_chain(chain)
    
    keyboard = []
    for token in popular_tokens:
        keyboard.append([InlineKeyboardButton(
            f"{token['symbol']} - {token['name']}", 
            callback_data=f"token_{token['address']}"
        )])
    
    keyboard.append([InlineKeyboardButton("🔍 Input Manual Contract Address", callback_data='manual_token_input')])
    keyboard.append([InlineKeyboardButton("⬅️ Kembali", callback_data='alert_menu')])
    
    text = f"💰 Pilih token di jaringan **{chain.title()}** yang ingin di-alert:"
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    return PILIH_TOKEN_ALERT

async def select_alert_token(update: Update, context):
    """User memilih token untuk alert"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith('token_'):
        token_address = query.data.split('_')[1]
        context.user_data['alert_token_address'] = token_address
        
        chain = context.user_data['alert_chain']
        token_info = await get_token_info(chain, token_address)
        current_price = await get_current_token_price(chain, token_address)
        
        context.user_data['token_info'] = token_info
        context.user_data['current_price'] = current_price
        
        text = (
            f"📊 **{token_info['symbol']} - {token_info['name']}**\n"
            f"🏷️ Harga saat ini: **${current_price:,.6f}**\n"
            f"🌐 Chain: **{chain.title()}**\n\n"
            "🎯 Pilih jenis alert yang diinginkan:"
        )
        
        keyboard = [
            [InlineKeyboardButton("📈 Alert Naik (Above)", callback_data='alert_type_above')],
            [InlineKeyboardButton("📉 Alert Turun (Below)", callback_data='alert_type_below')],
            [InlineKeyboardButton("📊 Alert Perubahan %", callback_data='alert_type_percent')],
            [InlineKeyboardButton("⬅️ Kembali", callback_data='create_new_alert')]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return PILIH_JENIS_ALERT
        
    elif query.data == 'manual_token_input':
        await query.edit_message_text(
            "📝 Kirimkan contract address token yang ingin di-alert:\n\n"
            "Contoh: `0xA0b86a33E6441c4C593E2C0E3e073ea20b6A4b9e`",
            parse_mode='Markdown'
        )
        return PILIH_TOKEN_ALERT

async def select_alert_type(update: Update, context):
    """User memilih jenis alert"""
    query = update.callback_query
    await query.answer()
    
    alert_type = query.data.split('_')[2]
    context.user_data['alert_type'] = alert_type
    
    token_info = context.user_data['token_info']
    current_price = context.user_data['current_price']
    
    if alert_type == 'above':
        text = (f"📈 **Alert Naik untuk {token_info['symbol']}**\n\nHarga saat ini: **${current_price:,.6f}**\n\n💰 Masukkan harga target (dalam USD):\nContoh: {current_price * 1.1:.6f} (naik 10%)")
    elif alert_type == 'below':
        text = (f"📉 **Alert Turun untuk {token_info['symbol']}**\n\nHarga saat ini: **${current_price:,.6f}**\n\n💰 Masukkan harga target (dalam USD):\nContoh: {current_price * 0.9:.6f} (turun 10%)")
    else:  # percent
        text = (f"📊 **Alert Perubahan % untuk {token_info['symbol']}**\n\nHarga saat ini: **${current_price:,.6f}**\n\n📈 Masukkan persentase perubahan:\nContoh: +10 (naik 10%) atau -15 (turun 15%)")
    
    await query.edit_message_text(text, parse_mode='Markdown')
    return SET_HARGA_TARGET

async def set_target_price(update: Update, context):
    """User memasukkan harga target atau persentase"""
    try:
        user_input = update.message.text.strip()
        alert_type = context.user_data['alert_type']
        
        if alert_type == 'percent':
            percentage = float(user_input.replace('%', '').replace('+', ''))
            context.user_data['target_percentage'] = percentage
            target_display = f"{percentage:+.1f}%"
        else:
            target_price = float(user_input)
            context.user_data['target_price'] = target_price
            target_display = f"${target_price:,.6f}"
        
        token_info = context.user_data['token_info']
        chain = context.user_data['alert_chain']
        current_price = context.user_data['current_price']
        
        alert_type_text = {'above': 'Naik di atas', 'below': 'Turun di bawah', 'percent': 'Berubah'}[alert_type]
        
        text = (
            "✅ **Konfirmasi Alert Harga**\n\n"
            f"🪙 Token: **{token_info['symbol']} ({token_info['name']})**\n"
            f"🌐 Chain: **{chain.title()}**\n"
            f"💰 Harga Saat Ini: **${current_price:,.6f}**\n"
            f"🎯 Alert: **{alert_type_text} {target_display}**\n\n"
            "Konfirmasi pembuatan alert?"
        )
        
        keyboard = [[InlineKeyboardButton("✅ Ya, Buat Alert", callback_data='confirm_create_alert')], [InlineKeyboardButton("❌ Batal", callback_data='alert_menu')]]
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except ValueError:
        await update.message.reply_text("❌ Format tidak valid! Masukkan angka yang benar.\nContoh: 3500 atau 10% atau +5")
        return SET_HARGA_TARGET
    
    return ConversationHandler.END

async def confirm_create_alert(update: Update, context):
    """Konfirmasi dan simpan alert ke database"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    alert_data = {
        'user_id': user_id,
        'token_address': context.user_data['alert_token_address'],
        'chain': context.user_data['alert_chain'],
        'alert_type': context.user_data['alert_type'],
        'target_price': context.user_data.get('target_price'),
        'target_percentage': context.user_data.get('target_percentage'),
        'token_symbol': context.user_data['token_info']['symbol']
    }
    
    alert_id = database.create_price_alert(alert_data)
    
    text = f"🎉 **Alert berhasil dibuat!**\n\n📋 ID Alert: **#{alert_id}**\n🔔 Anda akan mendapat notifikasi ketika kondisi tercapai." if alert_id else "❌ Gagal membuat alert. Silakan coba lagi."
    
    # PERBAIKAN ALUR PENGGUNA: Setelah membuat alert, panggil kembali menu alert
    await query.edit_message_text(text, parse_mode='Markdown')
    await alert_menu(update, context)


async def view_active_alerts(update: Update, context):
    """Tampilkan semua alert aktif user"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    alerts = database.get_user_active_alerts(user_id)
    
    if not alerts:
        text = "📭 **Tidak ada alert aktif**\n\nBuat alert pertama Anda untuk mendapatkan notifikasi harga real-time!"
        keyboard = [[InlineKeyboardButton("➕ Buat Alert Pertama", callback_data='create_new_alert')], [InlineKeyboardButton("⬅️ Kembali", callback_data='alert_menu')]]
    else:
        text = f"📋 **Alert Aktif Anda ({len(alerts)} alert)**\n\n"
        keyboard = []
        for i, alert in enumerate(alerts[:10]):
            alert_desc = format_alert_description(alert)
            text += f"**{i}.** {alert_desc}\n"
            keyboard.append([InlineKeyboardButton(f"🗑️ Hapus Alert #{alert['id']}", callback_data=f"delete_alert_{alert['id']}")])
        keyboard.append([InlineKeyboardButton("⬅️ Kembali", callback_data='alert_menu')])
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def popular_alerts(update: Update, context):
    """Menampilkan daftar alert token yang paling populer di kalangan pengguna."""
    query = update.callback_query
    await query.answer()

    popular_tokens = database.get_popular_alert_tokens() # Limit 10 sudah diatur di database.py
    text = "📈 **Alert Terpopuler Saat Ini**\n\n"

    if not popular_tokens:
        text += "Belum ada alert yang dibuat oleh pengguna."
    else:
        text += "Berikut adalah token yang paling sering dipantau oleh komunitas:\n\n"
        for i, token in enumerate(popular_tokens, 1):
            symbol = token['token_symbol']
            chain = token['chain'].title()
            count = token['alert_count']
            text += f"**{i}. {symbol}** di __{chain}__\n    (Dipantau oleh {count} pengguna)\n\n"

    keyboard = [[InlineKeyboardButton("⬅️ Kembali ke Menu Alert", callback_data='alert_menu')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


def get_popular_tokens_for_chain(chain):
    """Daftar token populer untuk setiap chain (statis)"""
    popular_tokens = {
        'ethereum': [
            {'symbol': 'USDC', 'name': 'USD Coin', 'address': '0xA0b86a33E6441c4C593E2C0E3e073ea20b6A4b9e'},
            {'symbol': 'USDT', 'name': 'Tether USD', 'address': '0xdAC17F958D2ee523a2206206994597C13D831ec7'},
            {'symbol': 'WETH', 'name': 'Wrapped Ether', 'address': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'},
            {'symbol': 'PEPE', 'name': 'Pepe', 'address': '0x6982508145454Ce325dDbE47a25d4ec3d2311933'},
        ],
        'base': [
            {'symbol': 'DEGEN', 'name': 'Degen', 'address': '0x4ed4E862860beD51a9570b96d89aF5E1B0Efefed'},
            {'symbol': 'WETH', 'name': 'Wrapped Ether', 'address': '0x4200000000000000000000000000000000000006'},
        ]
    }
    return popular_tokens.get(chain, [])

async def get_token_info(chain, token_address):
    """Ambil informasi token dari Alchemy"""
    chain_data = CHAIN_CONFIG.get(chain, {})
    # PERBAIKAN: Memanggil config.ALCHEMY_API_KEY, bukan database.config...
    rpc_url = f"https://{chain_data['rpc_subdomain']}.g.alchemy.com/v2/{config.ALCHEMY_API_KEY}"
    response = make_rpc_request(rpc_url, "alchemy_getTokenMetadata", [token_address])
    return response['result'] if response and 'result' in response else {'symbol': 'UNKNOWN', 'name': 'Unknown Token', 'decimals': 18}

async def get_current_token_price(chain, token_address):
    """Ambil harga token saat ini (implementasi sederhana)"""
    # Di implementasi nyata, integrate dengan price API seperti CoinGecko
    return random.uniform(0.001, 5000)

def format_alert_description(alert):
    """Format deskripsi alert untuk ditampilkan"""
    symbol = alert['token_symbol']
    alert_type = alert['alert_type']
    
    if alert_type == 'above':
        return f"{symbol} naik di atas ${alert['target_price']:,.6f}"
    elif alert_type == 'below':
        return f"{symbol} turun di bawah ${alert['target_price']:,.6f}"
    else: # percent
        return f"{symbol} berubah {alert['target_percentage']:+.1f}%"
