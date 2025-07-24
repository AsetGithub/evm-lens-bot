# bot/handlers/wallet_management.py

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ConversationHandler
import database
from bot.utils import get_network_keyboard
from bot.handlers.start import start

# Definisikan state untuk alur percakapan
GET_ADDRESS, SELECT_CHAIN, GET_ALIAS = range(3)

async def add_wallet_start(update: Update, context):
    query = update.callback_query; await query.answer()
    await query.edit_message_text(text="✍️ Oke, kirim alamat wallet (contoh: 0x...) yang ingin Anda pantau.")
    return GET_ADDRESS

async def get_address(update: Update, context):
    context.user_data['address'] = update.message.text
    await update.message.reply_text("🌐 Alamat diterima! Sekarang pilih jaringannya:", reply_markup=get_network_keyboard('chain_'))
    return SELECT_CHAIN

async def select_chain(update: Update, context):
    query = update.callback_query; await query.answer()
    context.user_data['chain'] = query.data.split('_')[1]
    await query.edit_message_text("📝 Terakhir, beri nama alias untuk wallet ini (contoh: Dompet Utama). Kirim /skip untuk menggunakan alamat sebagai nama.")
    return GET_ALIAS

async def get_alias(update: Update, context):
    alias = update.message.text
    user_id = update.effective_user.id
    address = context.user_data['address']
    chain = context.user_data['chain']
    success = database.add_wallet(user_id, address, chain, alias)
    text = f"✅ Berhasil! Wallet '{alias}' sekarang dipantau di jaringan {chain.title()}." if success else f"ℹ️ Wallet ini sudah ada di daftar pantauan Anda."
    await update.message.reply_text(text)
    await start(update, context)
    return ConversationHandler.END

async def skip_alias(update: Update, context):
    address = context.user_data['address']
    alias = f"{address[:6]}...{address[-4:]}"
    update.message.text = alias
    return await get_alias(update, context)

async def my_wallets(update: Update, context):
    query = update.callback_query; await query.answer()
    wallets = database.get_wallets_by_user(update.effective_user.id)
    text = "📂 **Wallet Anda:**\n\n" if wallets else "Anda belum menambahkan wallet."
    for _, address, chain, alias in wallets:
        display_name = alias if alias else f"{address[:6]}...{address[-4:]}"
        text += f"🔹 **{display_name}** ({chain.title()})\n   └ <code>{address}</code>\n"
    keyboard = [[InlineKeyboardButton("⬅️ Kembali", callback_data='main_menu')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def remove_wallet_menu(update: Update, context):
    query = update.callback_query; await query.answer()
    wallets = database.get_wallets_by_user(update.effective_user.id)
    if not wallets:
        await query.edit_message_text("Tidak ada wallet untuk dihapus.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Kembali", callback_data='main_menu')]]))
        return
    keyboard = []
    for wid, address, chain, alias in wallets:
        display_name = alias if alias else f"{address[:6]}...{address[-4:]}"
        keyboard.append([InlineKeyboardButton(f"❌ Hapus '{display_name}' ({chain.title()})", callback_data=f"delete_{wid}")])
    keyboard.append([InlineKeyboardButton("⬅️ Kembali", callback_data='main_menu')])
    await query.edit_message_text("Pilih wallet yang ingin dihapus:", reply_markup=InlineKeyboardMarkup(keyboard))

async def remove_wallet_confirm(update: Update, context):
    query = update.callback_query; await query.answer()
    wallet_id_to_delete = int(query.data.split('_')[1])
    success = database.remove_wallet_by_id(wallet_id_to_delete, update.effective_user.id)
    await query.edit_message_text("✅ Wallet berhasil dihapus." if success else "❌ Gagal menghapus wallet.")
    await start(update, context)
