# bot/handlers/start.py

from telegram import Update
from telegram.ext import ConversationHandler
from bot.utils import get_main_menu_keyboard

async def start(update: Update, context):
    """Mengirim pesan selamat datang dengan menu utama."""
    user = update.effective_user
    text = f"Halo {user.mention_html()}!\n\nSelamat datang di EVM Lens Bot. Siap membantumu memantau aset Web3. Pilih menu di bawah."
    
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(text=text, reply_markup=get_main_menu_keyboard(), parse_mode='HTML')
    else:
        await update.message.reply_html(text, reply_markup=get_main_menu_keyboard())
    
    return ConversationHandler.END
