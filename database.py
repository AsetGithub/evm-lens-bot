# database.py - Versi Final yang Sudah Diperbaiki

import sqlite3
from datetime import datetime

# Definisikan nama file database sebagai konstanta global
DATABASE_NAME = 'bot_database.db'

def get_db_connection():
    """Membuat koneksi ke database SQLite."""
    conn = sqlite3.connect(DATABASE_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def setup_database():
    """
    Membuat semua tabel yang diperlukan untuk bot (wallets dan semua tabel alert).
    Ini adalah satu-satunya fungsi setup yang perlu dipanggil dari main.py.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Tabel untuk manajemen wallet
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS wallets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            chain TEXT NOT NULL,
            address TEXT NOT NULL UNIQUE,
            alias TEXT
        );
    ''')
    
    # Tabel untuk menyimpan alert harga user
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS price_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token_address TEXT NOT NULL,
            token_symbol TEXT NOT NULL,
            chain TEXT NOT NULL,
            alert_type TEXT NOT NULL, -- 'above', 'below', 'percent'
            target_price REAL,
            target_percentage REAL,
            is_active BOOLEAN NOT NULL DEFAULT 1,
            is_triggered BOOLEAN NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            triggered_at TIMESTAMP
        )
    ''')
    
    # Tabel untuk log notifikasi yang sudah dikirim
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alert_notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            message_text TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (alert_id) REFERENCES price_alerts (id)
        )
    ''')
    
    # Tabel untuk statistik penggunaan alert
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alert_statistics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE UNIQUE NOT NULL,
            total_alerts_created INTEGER DEFAULT 0,
            total_alerts_triggered INTEGER DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Database setup selesai. Semua tabel sudah siap.")

def create_price_alert(alert_data):
    """Buat alert harga baru"""
    sql = '''
        INSERT INTO price_alerts (
            user_id, token_address, token_symbol, chain, alert_type,
            target_price, target_percentage
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    '''
    params = (
        alert_data['user_id'],
        alert_data['token_address'].lower(),
        alert_data['token_symbol'],
        alert_data['chain'].lower(),
        alert_data['alert_type'],
        alert_data.get('target_price'),
        alert_data.get('target_percentage')
    )
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        alert_id = cursor.lastrowid
        conn.commit()
        update_daily_alert_stats('created')
        return alert_id
    except sqlite3.Error as e:
        print(f"Error membuat alert: {e}")
        return None
    finally:
        conn.close()

def get_user_active_alerts(user_id):
    """Ambil semua alert aktif untuk user tertentu"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, token_symbol, chain, alert_type, target_price, target_percentage
        FROM price_alerts 
        WHERE user_id = ? AND is_active = 1 AND is_triggered = 0
        ORDER BY created_at DESC
    ''', (user_id,))
    alerts = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return alerts

def delete_price_alert(alert_id, user_id):
    """Hapus alert (sebenarnya menonaktifkan)"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE price_alerts SET is_active = 0 WHERE id = ? AND user_id = ?',
            (alert_id, user_id)
        )
        success = cursor.rowcount > 0
        conn.commit()
        return success
    except sqlite3.Error as e:
        print(f"Error hapus alert: {e}")
        return False
    finally:
        conn.close()

def update_daily_alert_stats(action_type):
    """Update statistik harian penggunaan alert"""
    today = datetime.now().date()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM alert_statistics WHERE date = ?', (today,))
        
        if cursor.fetchone():
            field = 'total_alerts_created' if action_type == 'created' else 'total_alerts_triggered'
            cursor.execute(f'UPDATE alert_statistics SET {field} = {field} + 1 WHERE date = ?', (today,))
        else:
            created = 1 if action_type == 'created' else 0
            triggered = 1 if action_type == 'triggered' else 0
            cursor.execute('INSERT INTO alert_statistics (date, total_alerts_created, total_alerts_triggered) VALUES (?, ?, ?)', (today, created, triggered))
        
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error update statistik: {e}")
    finally:
        conn.close()

# Anda bisa menambahkan fungsi-fungsi lain seperti get_all_active_alerts, trigger_price_alert, dll. di sini jika diperlukan.
# Tambahkan fungsi ini ke dalam file database.py

def get_active_chains():
    """
    Mengambil daftar unik semua 'chain' yang memiliki alert aktif
    dan belum ter-trigger untuk efisiensi monitoring.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT DISTINCT chain 
            FROM price_alerts 
            WHERE is_active = 1 AND is_triggered = 0
        ''')
        # Mengubah hasil query (list of tuples) menjadi list of strings
        active_chains = [row['chain'] for row in cursor.fetchall()]
        return active_chains
    except sqlite3.Error as e:
        print(f"Error mengambil active chains: {e}")
        return []
    finally:
        conn.close()

# Tambahkan fungsi ini ke dalam file database.py

def get_wallets_by_user(user_id):
    """Mengambil semua dompet yang terdaftar untuk seorang pengguna."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, alias, address, chain 
            FROM wallets 
            WHERE user_id = ?
        ''', (user_id,))

        wallets = [dict(row) for row in cursor.fetchall()]
        return wallets

    except sqlite3.Error as e:
        print(f"Error mengambil dompet pengguna: {e}")
        return []
    finally:
        conn.close()

# Tambahkan fungsi ini ke dalam file database.py

def add_wallet(user_id, address, chain, alias):
    """Menambahkan dompet baru ke database untuk seorang pengguna."""
    sql = '''
        INSERT INTO wallets (user_id, address, chain, alias) 
        VALUES (?, ?, ?, ?)
    '''
    params = (user_id, address.lower(), chain, alias)

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        conn.commit()
        return True # Sukses
    except sqlite3.IntegrityError:
        # Error ini terjadi jika alamat dompet sudah ada (karena ada UNIQUE constraint)
        print(f"Gagal menambahkan dompet: Alamat {address} sudah ada.")
        return False
    except sqlite3.Error as e:
        print(f"Error saat menambahkan dompet: {e}")
        return False
    finally:
        conn.close()

# Tambahkan fungsi ini ke dalam file database.py

def remove_wallet_by_id(wallet_id, user_id):
    """Menghapus dompet berdasarkan ID uniknya dan ID pemilik."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # Kita hapus langsung dari database
        cursor.execute(
            'DELETE FROM wallets WHERE id = ? AND user_id = ?',
            (wallet_id, user_id)
        )
        success = cursor.rowcount > 0 # rowcount > 0 berarti ada baris yang terhapus
        conn.commit()
        return success
    except sqlite3.Error as e:
        print(f"Error saat menghapus dompet by ID: {e}")
        return False
    finally:
        conn.close()


# Tambahkan fungsi ini ke dalam file database.py

def get_wallet_by_id(wallet_id, user_id):
    """Mengambil detail satu dompet berdasarkan ID uniknya dan ID pemilik."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # Ambil satu baris data, pastikan wallet_id dan user_id cocok
        cursor.execute(
            'SELECT id, address, chain, alias FROM wallets WHERE id = ? AND user_id = ?',
            (wallet_id, user_id)
        )
        wallet = cursor.fetchone() # fetchone() untuk satu hasil
        # Kembalikan sebagai dictionary jika ditemukan, jika tidak, None
        return dict(wallet) if wallet else None
    except sqlite3.Error as e:
        print(f"Error saat mengambil dompet by ID: {e}")
        return None
    finally:
        conn.close()


# Di dalam file database.py, cari fungsi setup_database()
# dan tambahkan cursor.execute() ini di dalamnya.

def setup_database():
    """Membuat semua tabel yang diperlukan untuk bot."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # ... (kode CREATE TABLE untuk wallets dan price_alerts yang sudah ada) ...

    # TAMBAHKAN INI:
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
            min_value_usd REAL DEFAULT 0,
            notify_on_airdrop BOOLEAN DEFAULT 1
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Database setup selesai. Semua tabel sudah siap.")


# Tambahkan kedua fungsi ini di mana saja di dalam file database.py

def get_user_settings(user_id):
    """Mengambil atau membuat pengaturan default untuk pengguna."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Cek apakah pengguna sudah punya pengaturan
    cursor.execute("SELECT * FROM user_settings WHERE user_id = ?", (user_id,))
    settings = cursor.fetchone()
    
    if not settings:
        # Jika tidak ada, buat pengaturan default dan simpan
        cursor.execute("INSERT INTO user_settings (user_id) VALUES (?)", (user_id,))
        conn.commit()
        # Ambil lagi pengaturan yang baru dibuat
        cursor.execute("SELECT * FROM user_settings WHERE user_id = ?", (user_id,))
        settings = cursor.fetchone()
        
    conn.close()
    return dict(settings)

def update_user_setting(user_id, key, value):
    """Memperbarui satu pengaturan spesifik untuk pengguna."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # Menggunakan format string yang aman untuk nama kolom
        sql = f"UPDATE user_settings SET {key} = ? WHERE user_id = ?"
        cursor.execute(sql, (value, user_id))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Error saat update setting: {e}")
        return False
    finally:
        conn.close()

