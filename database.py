# database.py - Extension untuk Price Alert System
# Indonesia: Tambahan fungsi database untuk sistem alert harga

import sqlite3
from datetime import datetime

# Indonesia: Tambahkan fungsi-fungsi ini ke database.py yang sudah ada

def setup_price_alerts_table():
    """Indonesia: Setup tabel untuk sistem alert harga"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    # Indonesia: Tabel untuk menyimpan alert harga user
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
            current_price_when_created REAL,
            is_active INTEGER DEFAULT 1,
            is_triggered INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            triggered_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES wallets (user_id)
        )
    ''')
    
    # Indonesia: Tabel untuk log notifikasi yang sudah dikirim
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alert_notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            notification_type TEXT NOT NULL, -- 'price_reached', 'reminder'
            message_text TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (alert_id) REFERENCES price_alerts (id)
        )
    ''')
    
    # Indonesia: Tabel untuk statistik penggunaan alert
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alert_statistics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL,
            total_alerts_created INTEGER DEFAULT 0,
            total_alerts_triggered INTEGER DEFAULT 0,
            most_popular_token TEXT,
            most_popular_chain TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Indonesia: Tabel price alerts berhasil dibuat.")

def create_price_alert(alert_data):
    """Indonesia: Buat alert harga baru"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO price_alerts (
                user_id, token_address, token_symbol, chain, alert_type,
                target_price, target_percentage, current_price_when_created
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            alert_data['user_id'],
            alert_data['token_address'].lower(),
            alert_data['token_symbol'],
            alert_data['chain'].lower(),
            alert_data['alert_type'],
            alert_data.get('target_price'),
            alert_data.get('target_percentage'),
            alert_data.get('current_price', 0)
        ))
        
        alert_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Indonesia: Update statistik
        update_daily_alert_stats('created')
        
        return alert_id
        
    except sqlite3.Error as e:
        print(f"Indonesia: Error membuat alert: {e}")
        conn.close()
        return None

def get_user_active_alerts(user_id):
    """Indonesia: Ambil semua alert aktif untuk user tertentu"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, token_address, token_symbol, chain, alert_type,
               target_price, target_percentage, created_at
        FROM price_alerts 
        WHERE user_id = ? AND is_active = 1 AND is_triggered = 0
        ORDER BY created_at DESC
    ''', (user_id,))
    
    alerts = []
    for row in cursor.fetchall():
        alerts.append({
            'id': row[0],
            'token_address': row[1],
            'token_symbol': row[2],
            'chain': row[3],
            'alert_type': row[4],
            'target_price': row[5],
            'target_percentage': row[6],
            'created_at': row[7]
        })
    
    conn.close()
    return alerts

def get_all_active_alerts():
    """Indonesia: Ambil semua alert aktif untuk monitoring"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, user_id, token_address, token_symbol, chain, alert_type,
               target_price, target_percentage, current_price_when_created
        FROM price_alerts 
        WHERE is_active = 1 AND is_triggered = 0
    ''')
    
    alerts = []
    for row in cursor.fetchall():
        alerts.append({
            'id': row[0],
            'user_id': row[1],
            'token_address': row[2],
            'token_symbol': row[3],
            'chain': row[4],
            'alert_type': row[5],
            'target_price': row[6],
            'target_percentage': row[7],
            'created_price': row[8]
        })
    
    conn.close()
    return alerts

def trigger_price_alert(alert_id, current_price):
    """Indonesia: Tandai alert sebagai triggered"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            UPDATE price_alerts 
            SET is_triggered = 1, triggered_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (alert_id,))
        
        conn.commit()
        conn.close()
        
        # Indonesia: Update statistik
        update_daily_alert_stats('triggered')
        
        return True
        
    except sqlite3.Error as e:
        print(f"Indonesia: Error trigger alert: {e}")
        conn.close()
        return False

def delete_price_alert(alert_id, user_id):
    """Indonesia: Hapus alert (hanya pemilik yang bisa hapus)"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            UPDATE price_alerts 
            SET is_active = 0 
            WHERE id = ? AND user_id = ?
        ''', (alert_id, user_id))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return success
        
    except sqlite3.Error as e:
        print(f"Indonesia: Error hapus alert: {e}")
        conn.close()
        return False

def log_alert_notification(alert_id, user_id, notification_type, message_text):
    """Indonesia: Log notifikasi yang sudah dikirim"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO alert_notifications (alert_id, user_id, notification_type, message_text)
            VALUES (?, ?, ?, ?)
        ''', (alert_id, user_id, notification_type, message_text))
        
        conn.commit()
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"Indonesia: Error log notifikasi: {e}")
        conn.close()
        return False

def update_daily_alert_stats(action_type):
    """Indonesia: Update statistik harian penggunaan alert"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    today = datetime.now().date()
    
    try:
        # Indonesia: Cek apakah sudah ada record untuk hari ini
        cursor.execute('SELECT id FROM alert_statistics WHERE date = ?', (today,))
        existing = cursor.fetchone()
        
        if existing:
            if action_type == 'created':
                cursor.execute('''
                    UPDATE alert_statistics 
                    SET total_alerts_created = total_alerts_created + 1,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE date = ?
                ''', (today,))
            elif action_type == 'triggered':
                cursor.execute('''
                    UPDATE alert_statistics 
                    SET total_alerts_triggered = total_alerts_triggered + 1,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE date = ?
                ''', (today,))
        else:
            # Indonesia: Buat record baru untuk hari ini
            created_count = 1 if action_type == 'created' else 0
            triggered_count = 1 if action_type == 'triggered' else 0
            
            cursor.execute('''
                INSERT INTO alert_statistics (date, total_alerts_created, total_alerts_triggered)
                VALUES (?, ?, ?)
            ''', (today, created_count, triggered_count))
        
        conn.commit()
        conn.close()
        
    except sqlite3.Error as e:
        print(f"Indonesia: Error update statistik: {e}")
        conn.close()

def get_popular_alert_tokens():
    """Indonesia: Ambil token yang paling banyak di-alert"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT token_symbol, chain, COUNT(*) as alert_count
        FROM price_alerts 
        WHERE created_at >= date('now', '-30 days')
        GROUP BY token_symbol, chain
        ORDER BY alert_count DESC
        LIMIT 10
    ''')
    
    popular_tokens = []
    for row in cursor.fetchall():
        popular_tokens.append({
            'symbol': row[0],
            'chain': row[1],
            'alert_count': row[2]
        })
    
    conn.close()
    return popular_tokens

def get_user_alert_summary(user_id):
    """Indonesia: Ambil ringkasan alert user (untuk laporan)"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    # Indonesia: Hitung total alert
    cursor.execute('SELECT COUNT(*) FROM price_alerts WHERE user_id = ?', (user_id,))
    total_alerts = cursor.fetchone()[0]
    
    # Indonesia: Hitung alert yang sudah triggered
    cursor.execute('SELECT COUNT(*) FROM price_alerts WHERE user_id = ? AND is_triggered = 1', (user_id,))
    triggered_alerts = cursor.fetchone()[0]
    
    # Indonesia: Hitung alert aktif
    cursor.execute('SELECT COUNT(*) FROM price_alerts WHERE user_id = ? AND is_active = 1 AND is_triggered = 0', (user_id,))
    active_alerts = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        'total_alerts': total_alerts,
        'triggered_alerts': triggered_alerts,
        'active_alerts': active_alerts,
        'success_rate': (triggered_alerts / total_alerts * 100) if total_alerts > 0 else 0
    }

# Indonesia: Jangan lupa panggil ini saat setup database
def setup_enhanced_database():
    """Indonesia: Setup database dengan semua tabel yang diperlukan"""
    setup_database()  # Indonesia: Setup tabel yang sudah ada
    setup_price_alerts_table()  # Indonesia: Setup tabel baru untuk alerts
