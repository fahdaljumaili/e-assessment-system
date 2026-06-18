# E-Assessment System

نظام تقييم إلكتروني مبني بـ Flask لإدارة الاختبارات بين المحاضرين والطلاب.

## المتطلبات

- Python 3.10+
- pip

## التثبيت والتشغيل

```bash
# إنشاء بيئة افتراضية (اختياري)
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

# تثبيت الحزم
pip install -r requirements.txt

# تهيئة قاعدة البيانات (أو ترقية قاعدة موجودة)
python scripts/init_db.py
# أو للترقية فقط:
python scripts/migrate_db.py

# تشغيل التطبيق (تطوير)
python app.py
```

افتح المتصفح على: http://localhost:5000

### تشغيل الإنتاج (Waitress)

```bash
# 1. انسخ الإعدادات وعدّلها
copy .env.example .env        # Windows
# cp .env.example .env        # Linux/macOS

# 2. في ملف .env — مهم جداً:
#    SECRET_KEY=سلسلة-عشوائية-طويلة
#    FLASK_DEBUG=0
#    SESSION_COOKIE_SECURE=1   # إذا استخدمت HTTPS

# 3. تشغيل خادم الإنتاج
python run_production.py
```

> **Windows:** Waitress مناسب للإنتاج على Windows. على Linux يمكن أيضاً استخدام Gunicorn مع `wsgi:app`.

```bash

> **ملاحظة للنشر:** حسابات التجربة (`1234` / `admin123`) مخصصة للتطوير فقط. غيّرها أو احذفها قبل الاستخدام الفعلي في الجامعة.

## النشر على GitHub

المشروع جاهز للنشر. لا يُرفع معه:
- مجلد `.venv`
- قاعدة البيانات `db.sqlite3`
- ملفات الطلاب في `submissions/`

```bash
git init
git add .
git commit -m "Initial commit: E-Assessment System"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/e-assessment-system.git
git push -u origin main
```

## حسابات تجريبية

| المستخدم | كلمة المرور | الدور |
|----------|-------------|-------|
| instructor1 | 1234 | محاضر |
| student1 | 1234 | طالب |
| admin1 | admin123 | مدير — إدارة المستخدمين |

## المتغيرات البيئية

| المتغير | الوصف | الافتراضي |
|---------|-------|-----------|
| `SECRET_KEY` | مفتاح جلسات Flask | قيمة غير آمنة — **إلزامي** في الإنتاج |
| `FLASK_DEBUG` | وضع التصحيح (`1` أو `0`) | `1` |
| `HOST` | عنوان الاستماع | `0.0.0.0` |
| `PORT` | المنفذ | `5000` |
| `SESSION_COOKIE_SECURE` | كوكيز آمنة عبر HTTPS (`1` أو `0`) | `0` |

## هيكل المشروع

```
app.py              # نقطة الدخول (تطوير)
run_production.py   # خادم إنتاج (Waitress)
wsgi.py             # WSGI للنشر خلف Nginx
config.py           # الإعدادات
db.py               # اتصال قاعدة البيانات
decorators.py       # حماية المسارات (تسجيل الدخول / الأدوار)
utils.py            # دوال مساعدة
routes/
  auth.py           # تسجيل الدخول والخروج
  instructor.py     # مسارات المحاضر
  student.py        # مسارات الطالب
  admin.py          # إدارة المستخدمين
  courses.py        # المقررات والتسجيل
templates/          # قوالب HTML
scripts/init_db.py  # تهيئة SQLite
```

## الميزات

- **المقررات**: إنشاء مقررات، تسجيل طلاب، استيراد CSV
- **الاختبارات**: ربط الاختبار بمقرر، جدولة تلقائية لوقت البدء
- إضافة أسئلة (ملف أو **اختيار من متعدد MCQ** مع تصحيح تلقائي)
- بدء/إنهاء الاختبار بمؤقت عدّ تنازلي
- رفع إجابات الطلاب مع التحقق من امتداد الملف
- **عرض الدرجات والملاحظات** للطالب بعد التصحيح
- تصحيح يدوي مع ملاحظات وتصدير درجات PDF
- إدارة المستخدمين (مدير النظام)
- حماية CSRF وتحقق من الصلاحيات

### استيراد طلاب عبر CSV

```csv
username,full_name,password
student2,Ahmed Ali,1234
student3,Sara Hassan,
```

العمود `username` إلزامي. إذا لم يُذكر `password` يُستخدم كلمة المرور الافتراضية من النموذج.
