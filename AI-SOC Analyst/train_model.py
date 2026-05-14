import numpy as np
import joblib
from sklearn.ensemble import IsolationForest
import sqlite3
import random
from faker import Faker

fake = Faker()

def generate_normal_training_data(num_samples=5000, num_features=5):
    """
    يولد بيانات تدريب طبيعية متعددة الأبعاد:
    - feature1: عدد الحزم في الثانية (packets/sec)
    - feature2: حجم البيانات (bytes/sec)
    - feature3: عدد محاولات الاتصال الفاشلة
    - feature4: تنوع المنافذ المستخدمة
    - feature5: الفاصل الزمني بين الطلبات (ms)
    """
    data = []
    for _ in range(num_samples):
        # سلوك طبيعي: توزيعات طبيعية مع قيم معقولة
        packets = np.random.normal(500, 100)          # 500 pkt/s عادة
        bytes_sec = np.random.normal(50_000, 10_000)  # 50 KB/s
        failed_logins = np.random.poisson(0.5)        # نادراً فشل
        port_diversity = np.random.uniform(1, 20)     # 1-20 منفذ مختلف
        inter_arrival = np.random.exponential(0.05)   # 50ms بين الطلبات
        
        data.append([packets, bytes_sec, failed_logins, port_diversity, inter_arrival])
    
    return np.array(data)

def train_isolation_forest():
    print("📊 Generating normal behavior data...")
    X_train = generate_normal_training_data(8000)
    
    print("🧠 Training Isolation Forest (contamination=0.05)...")
    model = IsolationForest(contamination=0.05, random_state=42, n_estimators=100)
    model.fit(X_train)
    
    # حفظ النموذج
    joblib.dump(model, 'models/isolation_forest.pkl')
    print("✅ Model saved to models/isolation_forest.pkl")

if __name__ == '__main__':
    import os
    os.makedirs('models', exist_ok=True)
    train_isolation_forest()