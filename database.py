# database.py (Versi dengan Alias & Settings)

import sqlite3

DATABASE_NAME = 'wallets.db'

def setup_database():
    """Mempersiapkan semua tabel yang dibutuhkan."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    # Tambahkan kolom 'alias' ke tabel wallets
    try:
        cursor.execute("ALTER TABLE wallets ADD COLUMN alias TEXT")
    except sqlite3.OperationalError:
        pass # Kolom sudah ada

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS wallets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            wallet_address TEXT NOT NULL,
            chain TEXT NOT NULL,
            alias TEXT,
            UNIQUE(user_id, wallet_address, chain)
        )
    ''')
    
    # Buat tabel baru untuk pengaturan pengguna
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
            min_value_usd REAL DEFAULT 0,
            notify_on_airdrop INTEGER DEFAULT 1 -- 1 for True, 0 for False
        )
    ''')
    conn.commit()
    conn.close()
    print("Database siap digunakan dengan skema terbaru.")

def add_wallet(user_id, wallet_address, chain, alias):
    """Menambahkan wallet baru dengan alias."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO wallets (user_id, wallet_address, chain, alias) VALUES (?, ?, ?, ?)",
            (user_id, wallet_address.lower(), chain.lower(), alias)
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

def get_wallets_by_user(user_id):
    """Mengambil semua wallet, sekarang termasuk alias."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, wallet_address, chain, alias FROM wallets WHERE user_id = ?", (user_id,))
    wallets = cursor.fetchall()
    conn.close()
    return wallets

def get_wallet_by_id(wallet_id, user_id):
    """Mengambil detail satu wallet berdasarkan ID uniknya."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT wallet_address, chain FROM wallets WHERE id = ? AND user_id = ?", (wallet_id, user_id))
    wallet = cursor.fetchone()
    conn.close()
    return wallet

def remove_wallet_by_id(wallet_id, user_id):
    """Menghapus wallet berdasarkan ID uniknya."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM wallets WHERE id = ? AND user_id = ?", (wallet_id, user_id))
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success

def get_active_chains():
    """Mengambil daftar unik semua jaringan yang memiliki wallet terdaftar."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT chain FROM wallets")
    chains = [row[0] for row in cursor.fetchall()]
    conn.close()
    return chains

def get_user_settings(user_id):
    """Mengambil pengaturan untuk seorang pengguna."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO user_settings (user_id) VALUES (?)", (user_id,))
    conn.commit()
    cursor.execute("SELECT min_value_usd, notify_on_airdrop FROM user_settings WHERE user_id = ?", (user_id,))
    settings = cursor.fetchone()
    conn.close()
    if settings:
        return {'min_value_usd': settings[0], 'notify_on_airdrop': bool(settings[1])}
    else:
        return {'min_value_usd': 0, 'notify_on_airdrop': True}

def update_user_setting(user_id, key, value):
    """Memperbarui satu pengaturan spesifik untuk pengguna."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    if key not in ['min_value_usd', 'notify_on_airdrop']:
        return False
    if isinstance(value, bool):
        value = 1 if value else 0
    cursor.execute(f"UPDATE user_settings SET {key} = ? WHERE user_id = ?", (value, user_id))
    conn.commit()
    conn.close()
    return True
