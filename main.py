# main.py - Updated dengan Price Alert System
# Indonesia: Bot utama dengan fitur alert harga

import logging
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler,
    filters, ConversationHandler
)

import config
import database

# Indonesia: Import semua handler yang sudah ada
from bot.handlers.start import start
from bot.handlers.help import help_command
from bot.handlers.wallet_management import (
    add_wallet_start, get_address, select_chain, get_alias, skip_alias,
    my_wallets, remove_wallet_menu, remove_wallet_confirm,
    GET_ADDRESS, SELECT_CHAIN, GET_ALIAS
)
from bot.handlers.portfolio import (
    portfolio_start, portfolio_select_asset_type,
    get_portfolio_erc20, get_portfolio_nft
)
from bot.handlers.settings import (
    settings_menu, set_min_value_start, set_min_value_received,
    toggle_airdrop, SET_MIN_VALUE
)
from bot.handlers.gas_tracker import gas_start, get_gas_price

# Indonesia: Import handler baru untuk price alerts
from bot.handlers.price_alerts import (
    alert_menu, create_alert_start, select_alert_chain, select_alert_token,
    select_alert_type, set_target_price, confirm_create_alert, view_active_alerts,
    PILIH_CHAIN_ALERT, PILIH_TOKEN_ALERT, SET_HARGA_TARGET, PILIH_JENIS_ALERT
)

def main():
    """Indonesia: Fungsi utama untuk menjalankan bot dengan fitur lengkap"""
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    
    # Indonesia: Setup database dengan tabel baru untuk alerts
    database.setup_enhanced_database()
    
    application = Application.builder().token(config.TELEGRAM_TOKEN).build()

    # Indonesia: Conversation handler untuk tambah wallet (yang sudah ada)
    add_wallet_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_wallet_start, pattern='^add_wallet_start$')],
        states={
            GET_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_address)],
            SELECT_CHAIN: [CallbackQueryHandler(select_chain, pattern='^chain_')],
            GET_ALIAS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_alias), CommandHandler('skip', skip_alias)],
        },
        fallbacks=[CommandHandler('start', start), CallbackQueryHandler(start, pattern='^main_menu$')]
    )
    
    # Indonesia: Conversation handler untuk settings (yang sudah ada)
    settings_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(set_min_value_start, pattern='^set_min_value_start$')],
        states={ SET_MIN_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_min_value_received)] },
        fallbacks=[CommandHandler('start', start), CallbackQueryHandler(start, pattern='^main_menu$')]
    )

    # Indonesia: BARU - Conversation handler untuk price alerts
    price_alert_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(create_alert_start, pattern='^create_new_alert$')],
        states={
            PILIH_CHAIN_ALERT: [CallbackQueryHandler(select_alert_chain, pattern='^alert_chain_')],
            PILIH_TOKEN_ALERT: [
                CallbackQueryHandler(select_alert_token, pattern='^token_'),
                CallbackQueryHandler(select_alert_token, pattern='^manual_token_input$'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, select_alert_token)
            ],
            PILIH_JENIS_ALERT: [CallbackQueryHandler(select_alert_type, pattern='^alert_type_')],
            SET_HARGA_TARGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_target_price)],
        },
        fallbacks=[
            CommandHandler('start', start), 
            CallbackQueryHandler(start, pattern='^main_menu$'),
            CallbackQueryHandler(alert_menu, pattern='^alert_menu$')
        ]
    )

    # Indonesia: Daftarkan semua handler yang sudah ada
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("gas", gas_start))
    
    # Indonesia: BARU - Command untuk akses cepat price alerts
    application.add_handler(CommandHandler("alerts", lambda update, context: alert_menu(update, context)))
    application.add_handler(CommandHandler("alert", lambda update, context: alert_menu(update, context)))
    
    # Indonesia: Handler conversations
    application.add_handler(add_wallet_conv)
    application.add_handler(settings_conv)
    application.add_handler(price_alert_conv)  # Indonesia: BARU
    
    # Indonesia: Handler untuk wallet management
    application.add_handler(CallbackQueryHandler(my_wallets, pattern='^my_wallets$'))
    application.add_handler(CallbackQueryHandler(remove_wallet_menu, pattern='^remove_wallet_menu$'))
    application.add_handler(CallbackQueryHandler(remove_wallet_confirm, pattern='^delete_'))
    
    # Indonesia: Handler untuk portfolio
    application.add_handler(CallbackQueryHandler(portfolio_start, pattern='^portfolio_start$'))
    application.add_handler(CallbackQueryHandler(portfolio_select_asset_type, pattern='^portfolio_select_'))
    application.add_handler(CallbackQueryHandler(get_portfolio_erc20, pattern='^portfolio_erc20_'))
    application.add_handler(CallbackQueryHandler(get_portfolio_nft, pattern='^portfolio_nft_'))
    
    # Indonesia: Handler untuk settings
    application.add_handler(CallbackQueryHandler(settings_menu, pattern='^settings_menu$'))
    application.add_handler(CallbackQueryHandler(toggle_airdrop, pattern='^toggle_airdrop$'))
    
    # Indonesia: Handler untuk gas tracker
    application.add_handler(CallbackQueryHandler(gas_start, pattern='^gas_start$'))
    application.add_handler(CallbackQueryHandler(get_gas_price, pattern='^gas_'))
    
    # Indonesia: BARU - Handler untuk price alerts
    application.add_handler(CallbackQueryHandler(alert_menu, pattern='^alert_menu$'))
    application.add_handler(CallbackQueryHandler(view_active_alerts, pattern='^view_active_alerts$'))
    application.add_handler(CallbackQueryHandler(confirm_create_alert, pattern='^confirm_create_alert$'))
    
    # Indonesia: BARU - Handler untuk hapus alert
    async def delete_alert_handler(update, context):
        query = update.callback_query
        await query.answer()
        
        alert_id = int(query.data.split('_')[2])  # delete_alert_123
        user_id = update.effective_user.id
        
        success = database.delete_price_alert(alert_id, user_id)
        
        if success:
            await query.edit_message_text(
                "✅ Alert berhasil dihapus!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📋 Lihat Alert Lain", callback_data='view_active_alerts'),
                    InlineKeyboardButton("⬅️ Menu Utama", callback_data='main_menu')
                ]])
            )
        else:
            await query.edit_message_text("❌ Gagal menghapus alert.")
    
    application.add_handler(CallbackQueryHandler(delete_alert_handler, pattern='^delete_alert_'))
    
    # Indonesia: Handler untuk kembali ke main menu
    application.add_handler(CallbackQueryHandler(start, pattern='^main_menu$'))
    
    print("🇮🇩 Indonesia: Bot berjalan dengan fitur Price Alert System!")
    print("🚀 Fitur tersedia:")
    print("   - Wallet Management")
    print("   - Portfolio Tracking") 
    print("   - Gas Fee Tracker")
    print("   - 🆕 Price Alert System")
    print("   - Settings & Notifications")
    
    application.run_polling()

if __name__ == '__main__':
    main()
