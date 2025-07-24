# main.py

import logging
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler,
    filters, ConversationHandler
)

import config
import database

# Import semua handler
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

def main():
    """Fungsi utama untuk menjalankan bot."""
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    
    database.setup_database()
    application = Application.builder().token(config.TELEGRAM_TOKEN).build()

    # Conversation handler untuk tambah wallet
    add_wallet_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_wallet_start, pattern='^add_wallet_start$')],
        states={
            GET_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_address)],
            SELECT_CHAIN: [CallbackQueryHandler(select_chain, pattern='^chain_')],
            GET_ALIAS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_alias), CommandHandler('skip', skip_alias)],
        },
        fallbacks=[CommandHandler('start', start), CallbackQueryHandler(start, pattern='^main_menu$')]
    )
    
    # Conversation handler untuk settings
    settings_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(set_min_value_start, pattern='^set_min_value_start$')],
        states={ SET_MIN_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_min_value_received)] },
        fallbacks=[CommandHandler('start', start), CallbackQueryHandler(start, pattern='^main_menu$')]
    )

    # Daftarkan semua handler
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("gas", gas_start))
    
    application.add_handler(add_wallet_conv)
    application.add_handler(settings_conv)
    
    application.add_handler(CallbackQueryHandler(my_wallets, pattern='^my_wallets$'))
    application.add_handler(CallbackQueryHandler(remove_wallet_menu, pattern='^remove_wallet_menu$'))
    application.add_handler(CallbackQueryHandler(remove_wallet_confirm, pattern='^delete_'))
    
    application.add_handler(CallbackQueryHandler(portfolio_start, pattern='^portfolio_start$'))
    application.add_handler(CallbackQueryHandler(portfolio_select_asset_type, pattern='^portfolio_select_'))
    application.add_handler(CallbackQueryHandler(get_portfolio_erc20, pattern='^portfolio_erc20_'))
    application.add_handler(CallbackQueryHandler(get_portfolio_nft, pattern='^portfolio_nft_'))
    
    application.add_handler(CallbackQueryHandler(settings_menu, pattern='^settings_menu$'))
    application.add_handler(CallbackQueryHandler(toggle_airdrop, pattern='^toggle_airdrop$'))
    
    application.add_handler(CallbackQueryHandler(gas_start, pattern='^gas_start$'))
    application.add_handler(CallbackQueryHandler(get_gas_price, pattern='^gas_'))
    
    application.add_handler(CallbackQueryHandler(start, pattern='^main_menu$'))
    
    print("Bot berjalan dengan struktur baru dan semua fitur...")
    application.run_polling()

if __name__ == '__main__':
    main()