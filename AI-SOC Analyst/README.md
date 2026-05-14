# 1. تثبيت المتطلبات
pip install -r requirements.txt

# 2. إنشاء قاعدة البيانات
python init_db.py

# 3. تدريب نموذج IsolationForest (مرة واحدة)
python train_model.py

# 4. إعداد متغيرات البيئة (انسخ .env.example إلى .env وأضف توكن تلغرام)

# 5. تشغيل التطبيق
python app.py

# افتح المتصفح على http://localhost:5000