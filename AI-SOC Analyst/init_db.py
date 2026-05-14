import sqlite3

def init_database():
    conn = sqlite3.connect('soc_logs.db')
    cursor = conn.cursor()
    
    # جدول الأجهزة مع السمات الأساسية
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS devices (
            device_id TEXT PRIMARY KEY,
            device_name TEXT,
            ip_address TEXT,
            os_type TEXT,
            role TEXT
        )
    ''')
    
    # جدول السجلات الخام (كل قراءة)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS raw_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            device_id TEXT,
            metric_type TEXT,
            metric_value REAL,
            attack_type TEXT,
            is_anomaly BOOLEAN,
            FOREIGN KEY(device_id) REFERENCES devices(device_id)
        )
    ''')
    
    # جدول التنبيهات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            device_id TEXT,
            attack_type TEXT,
            severity TEXT,
            metric_value REAL,
            description TEXT,
            telegram_sent BOOLEAN DEFAULT 0,
            FOREIGN KEY(device_id) REFERENCES devices(device_id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized.")

if __name__ == '__main__':
    init_database()