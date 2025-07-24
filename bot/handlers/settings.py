# bot/handlers/settings.py

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ConversationHandler, MessageHandler, filters, CommandHandler
import database
from bot.handlers.start import start

SET_MIN_VALUE = range(4, 5)

async def settings_menu(update: Update, context):
    query = update.callback_query; await query.answer()
    user_id = update.effective_user.id
    settings = database.get_user_settings(user_id)
    
    min_val_text = f"${settings['min_value_usd']}" if settings['min_value_usd'] > 0 else "Tidak ada"
    airdrop_text = "✅ Aktif" if settings['notify_on_airdrop'] else "❌ Nonaktif"
    
    text = (
        "**⚙️ Pengaturan Notifikasi**\n\n"
        "Atur preferensi Anda untuk notifikasi transaksi.\n\n"
        f"- **Nilai Minimum:** {min_val_text}\n"
        f"- **Notifikasi Airdrop:** {airdrop_text}"
    )
    
    keyboard = [
        [InlineKeyboardButton("💲 Ubah Nilai Minimum", callback_data='set_min_value_start')],
        [InlineKeyboardButton(f"Toggle Airdrop ({'Matikan' if settings['notify_on_airdrop'] else 'Aktifkan'})", callback_data='toggle_airdrop')],
        [InlineKeyboardButton("⬅️ Kembali ke Menu Utama", callback_data='main_menu')]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def set_min_value_start(update: Update, context):
    query = update.callback_query; await query.answer()
    await query.edit_message_text("Masukkan nilai minimum transaksi dalam USD (contoh: 50). Kirim 0 untuk menonaktifkan.")
    return SET_MIN_VALUE

async def set_min_value_received(update: Update, context):
    try:
        value = float(update.message.text)
        database.update_user_setting(update.effective_user.id, 'min_value_usd', value)
        await update.message.reply_text(f"✅ Nilai minimum berhasil diatur ke ${value}.")
    except ValueError:
        await update.message.reply_text("❌ Input tidak valid. Harap masukkan angka.")
    
    await start(update, context)
    return ConversationHandler.END

async def toggle_airdrop(update: Update, context):
    query = update.callback_query; await query.answer()
    user_id = update.effective_user.id
    settings = database.get_user_settings(user_id)
    new_value = not settings['notify_on_airdrop']
    database.update_user_setting(user_id, 'notify_on_airdrop', new_value)
    await settings_menu(update, context) # Refresh menu