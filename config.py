import os

# Ambil token dari environment variable yang akan kita set nanti
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
ALCHEMY_WSS_URL = os.getenv('ALCHEMY_WSS_URL')

# Cek apakah token ada, jika tidak, program akan berhenti dengan pesan error
if not TELEGRAM_TOKEN:
    raise ValueError("Token Telegram tidak ditemukan! Mohon set environment variable TELEGRAM_TOKEN.")

if not ALCHEMY_WSS_URL:
    raise ValueError("URL WebSocket Alchemy tidak ditemukan! Mohon set environment variable ALCHEMY_WSS_URL.")