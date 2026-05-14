import os
import time
import threading
import random
import sqlite3
import numpy as np
import joblib
from flask import Flask, render_template, jsonify
from faker import Faker
import requests
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
app = Flask(__name__)
fake = Faker()

# ---------- إعدادات تلغرام ----------
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_alert(alert_data):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    message = (f"🚨 <b>AI-SOC ALERT</b> 🚨\n"
               f"<b>Device:</b> {alert_data['device_id']}\n"
               f"<b>Attack:</b> {alert_data['attack_type']}\n"
               f"<b>Severity:</b> {alert_data['severity']}\n"
               f"<b>Value:</b> {alert_data['metric_value']}\n"
               f"<b>Time:</b> {alert_data['alert_time']}")
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}, timeout=2)
    except:
        pass

# ---------- قاعدة البيانات ----------
DB_PATH = "soc_logs.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ---------- تحميل النموذج ----------
model = joblib.load('models/isolation_forest.pkl')

# ---------- تعريف أنواع الهجمات ----------
ATTACKS = {
    "DDoS": {
        "features_modifier": lambda f: [f[0]*15, f[1]*20, f[2]+2, f[3]*3, f[4]*0.1],
        "severity": "Critical",
        "description": "طلب كثيف جداً يغرق الخدمة"
    },
    "Data Exfiltration": {
        "features_modifier": lambda f: [f[0]*0.8, f[1]*8, f[2]+1, f[3]*2, f[4]*1.2],
        "severity": "High",
        "description": "نقل كمية كبيرة من البيانات للخارج"
    },
    "Brute Force": {
        "features_modifier": lambda f: [f[0]*1.2, f[1]*0.5, f[2]+20, f[3]*1.1, f[4]*0.9],
        "severity": "Medium",
        "description": "محاولات دخول متكررة بكلمات سر مختلفة"
    },
    "Malware": {
        "features_modifier": lambda f: [f[0]*3, f[1]*4, f[2]+5, f[3]*5, f[4]*0.5],
        "severity": "High",
        "description": "نشاط غير طبيعي يشبه البرمجيات الخبيثة"
    },
    "Port Scan": {
        "features_modifier": lambda f: [f[0]*2, f[1]*0.2, f[2]+0, f[3]*10, f[4]*0.3],
        "severity": "Low",
        "description": "مسح ضوئي للمنافذ"
    }
}

# ---------- توليد أجهزة حقيقية ----------
def init_devices(num=1000):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM devices")  # تنظيف سريع
    for i in range(1, num+1):
        device_id = f"D{i:04d}"
        name = fake.hostname()
        ip = fake.ipv4()
        os_choice = random.choice(["Windows Server", "Linux Ubuntu", "CentOS", "macOS", "FreeBSD"])
        role = random.choice(["Web Server", "DB Server", "Client", "Firewall", "Load Balancer"])
        cursor.execute("INSERT OR REPLACE INTO devices (device_id, device_name, ip_address, os_type, role) VALUES (?,?,?,?,?)",
                       (device_id, name, ip, os_choice, role))
    conn.commit()
    conn.close()
    print(f"✅ {num} devices initialized in DB.")

# ---------- توليد قيم طبيعية عشوائية متعددة الأبعاد ----------
def generate_normal_features():
    return [
        np.random.normal(500, 100),    # packets/sec
        np.random.normal(50000, 10000), # bytes/sec
        np.random.poisson(0.5),        # failed logins
        np.random.uniform(1, 20),      # port diversity
        np.random.exponential(0.05)    # inter-arrival time (sec)
    ]

def generate_attack_features(base_features, attack_name):
    attack = ATTACKS[attack_name]
    return attack["features_modifier"](base_features)

# ---------- دورة المحاكاة ----------
stop_simulation = False
SIMULATION_INTERVAL = 30   # ثانية

def simulation_loop():
    global stop_simulation
    conn = get_db()
    cursor = conn.cursor()
    
    while not stop_simulation:
        start_cycle = time.time()
        
        # جلب جميع الأجهزة
        cursor.execute("SELECT device_id FROM devices")
        devices = cursor.fetchall()
        
        for (device_id,) in devices:
            # 85% طبيعي، 15% هجوم (لتوليد تنبيهات كافية)
            if random.random() < 0.15:
                attack_type = random.choice(list(ATTACKS.keys()))
                normal_feat = generate_normal_features()
                features = generate_attack_features(normal_feat, attack_type)
                is_anomaly = 1
            else:
                features = generate_normal_features()
                attack_type = None
                is_anomaly = 0
            
            # تنبؤ النموذج (-1 شاذ، 1 طبيعي)
            pred = model.predict([features])[0]
            is_model_anomaly = (pred == -1)
            
            # إذا كان هناك تطابق مع الهجوم أو النموذج يشير إلى شذوذ
            final_anomaly = is_anomaly or is_model_anomaly
            if final_anomaly and not is_anomaly:
                attack_type = "Unknown Anomaly"
            
            # تخزين السجل الخام
            cursor.execute('''
                INSERT INTO raw_logs (device_id, metric_type, metric_value, attack_type, is_anomaly)
                VALUES (?, ?, ?, ?, ?)
            ''', (device_id, "multi_feature", float(np.mean(features)), attack_type, final_anomaly))
            
            # إذا كان شاذاً، سجل تنبيهاً
            if final_anomaly:
                severity = ATTACKS.get(attack_type, {}).get("severity", "Medium") if attack_type != "Unknown Anomaly" else "Medium"
                desc = ATTACKS.get(attack_type, {}).get("description", "سلوك غير طبيعي اكتشفه النموذج")
                cursor.execute('''
                    INSERT INTO alerts (device_id, attack_type, severity, metric_value, description, telegram_sent)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (device_id, attack_type, severity, float(np.mean(features)), desc, 0))
                
                # إرسال تلغرام (مع تبريد بسيط - نستخدم تخزين مؤقت في الذاكرة)
                alert_data = {
                    "device_id": device_id,
                    "attack_type": attack_type,
                    "severity": severity,
                    "metric_value": round(float(np.mean(features)),2),
                    "alert_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                send_telegram_alert(alert_data)
        
        conn.commit()
        
        elapsed = time.time() - start_cycle
        sleep_time = max(0, SIMULATION_INTERVAL - elapsed)
        time.sleep(sleep_time)
    
    conn.close()

# ---------- API endpoints ----------
@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/stats')
def stats():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM devices")
    total_devices = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM alerts WHERE alert_time > datetime('now', '-1 hour')")
    alerts_last_hour = cursor.fetchone()[0]
    cursor.execute("SELECT attack_type, COUNT(*) FROM alerts WHERE alert_time > datetime('now', '-1 hour') GROUP BY attack_type")
    attack_counts = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()
    return jsonify({
        "total_devices": total_devices,
        "alerts_last_hour": alerts_last_hour,
        "attack_breakdown": attack_counts,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

@app.route('/api/alerts')
def get_alerts():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT alert_time, device_id, attack_type, severity, metric_value, description
        FROM alerts ORDER BY alert_time DESC LIMIT 50
    ''')
    rows = cursor.fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])

@app.route('/api/anomaly_devices')
def anomaly_devices():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT DISTINCT device_id, attack_type, severity 
        FROM alerts WHERE alert_time > datetime('now', '-10 minutes')
        ORDER BY alert_time DESC LIMIT 100
    ''')
    rows = cursor.fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])

# ---------- بدء الخادم ----------
if __name__ == '__main__':
    init_devices(1000)
    # تشغيل خلفية المحاكاة
    sim_thread = threading.Thread(target=simulation_loop, daemon=True)
    sim_thread.start()
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)