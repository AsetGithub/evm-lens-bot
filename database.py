import sqlite3

DATABASE_NAME = 'wallets.db'

def setup_database():
    """Membuat tabel jika belum ada."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS wallets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            wallet_address TEXT NOT NULL,
            chain TEXT NOT NULL,
            UNIQUE(user_id, wallet_address, chain)
        )
    ''')
    conn.commit()
    conn.close()
    print("Database siap digunakan.")

def add_wallet(user_id, wallet_address, chain):
    """Menambahkan wallet baru ke database."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO wallets (user_id, wallet_address, chain) VALUES (?, ?, ?)",
            (user_id, wallet_address.lower(), chain.lower())
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        # Terjadi jika wallet sudah ada (karena aturan UNIQUE)
        conn.close()
        return False
        
        # (kode yang sudah ada di atas biarkan saja)

def get_all_wallets_by_chain(chain):
    """Mengambil semua alamat wallet unik untuk jaringan tertentu."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT wallet_address FROM wallets WHERE chain = ?", (chain.lower(),))
    wallets = [row[0] for row in cursor.fetchall()]
    conn.close()
    return wallets

def get_users_for_wallet(wallet_address, chain):
    """Mendapatkan semua user_id yang memantau wallet tertentu."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_id FROM wallets WHERE wallet_address = ? AND chain = ?",
        (wallet_address.lower(), chain.lower())
    )
    user_ids = [row[0] for row in cursor.fetchall()]
    conn.close()
    return user_ids