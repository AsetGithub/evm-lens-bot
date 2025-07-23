import os

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
# Pastikan variabel ini yang digunakan, bukan ALCHEMY_WSS_URL
ALCHEMY_API_KEY = os.getenv('ALCHEMY_API_KEY')

if not TELEGRAM_TOKEN:
    raise ValueError("Token Telegram tidak ditemukan! Mohon set environment variable TELEGRAM_TOKEN.")

if not ALCHEMY_API_KEY:
    raise ValueError("Kunci API Alchemy tidak ditemukan! Mohon set environment variable ALCHEMY_API_KEY.")
