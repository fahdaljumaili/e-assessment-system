# E-Assessment System

نظام تقييم إلكتروني مبني بـ **Flask** لإدارة الاختبارات والمقررات الدراسية بين المحاضرين والطلاب والمشرفين.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=flat&logo=flask&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?style=flat&logo=sqlite&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey?style=flat)
![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=flat)

---

## 🖼️ لقطات الشاشة

### صفحة تسجيل الدخول
![Login Page](docs/screenshots/login.png)

### لوحة تحكم المحاضر
![Instructor Dashboard](docs/screenshots/instructor_dashboard.png)

### لوحة تحكم الطالب
![Student Dashboard](docs/screenshots/student_dashboard.png)

### صفحة المقررات
![Courses Page](docs/screenshots/courses.png)

---

## 📋 المحتويات

- [لقطات الشاشة](#️-لقطات-الشاشة)
- [المتطلبات](#المتطلبات)
- [التثبيت والتشغيل](#التثبيت-والتشغيل)
- [تشغيل الإنتاج](#تشغيل-الإنتاج-waitress)
- [المتغيرات البيئية](#المتغيرات-البيئية)
- [هيكل المشروع](#هيكل-المشروع)
- [قاعدة البيانات](#قاعدة-البيانات)
- [الميزات](#الميزات)
- [حسابات تجريبية](#حسابات-تجريبية)
- [استيراد الطلاب عبر CSV](#استيراد-الطلاب-عبر-csv)
- [الأمان](#الأمان)
- [النشر على GitHub](#النشر-على-github)

---

## المتطلبات

- Python 3.10 أو أحدث
- pip

### الحزم المستخدمة

| الحزمة | الإصدار | الغرض |
|--------|---------|--------|
| Flask | ≥ 3.0 | إطار العمل الرئيسي |
| Werkzeug | ≥ 3.0 | تشفير كلمات المرور ومعالجة الملفات |
| Flask-WTF | ≥ 1.2 | حماية CSRF للنماذج |
| Jinja2 | ≥ 3.1 | محرك القوالب HTML |
| ReportLab | ≥ 4.0 | توليد ملفات PDF لتقارير الدرجات |
| Waitress | ≥ 3.0 | خادم إنتاج متوافق مع Windows |

---

## التثبيت والتشغيل

```bash
# 1. إنشاء بيئة افتراضية (موصى به)
python -m venv .venv

# تفعيل البيئة الافتراضية
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

# 2. تثبيت الحزم المطلوبة
pip install -r requirements.txt

# 3. تهيئة قاعدة البيانات (أول مرة فقط)
python scripts/init_db.py

# 4. تشغيل التطبيق في وضع التطوير
python app.py
```

افتح المتصفح على: **http://localhost:5000**

> **ملاحظة:** إذا كانت قاعدة البيانات موجودة مسبقاً وتريد ترقيتها فقط:
> ```bash
> python scripts/migrate_db.py
> ```

---

## تشغيل الإنتاج (Waitress)

```bash
# 1. انسخ ملف الإعدادات وعدّله
copy .env.example .env        # Windows
# cp .env.example .env        # Linux/macOS

# 2. في ملف .env — مهم جداً قبل النشر:
#    SECRET_KEY=سلسلة-عشوائية-طويلة-وآمنة
#    FLASK_DEBUG=0
#    SESSION_COOKIE_SECURE=1   # عند استخدام HTTPS فقط

# 3. تشغيل خادم الإنتاج
python run_production.py
```

> **Windows:** Waitress هو الخيار الموصى به للإنتاج على Windows.
> **Linux:** يمكن استخدام Gunicorn بدلاً منه عبر: `gunicorn wsgi:app`

> **تنبيه للنشر الفعلي:** حسابات التجربة (`1234` / `admin123`) مخصصة للتطوير فقط. يجب تغييرها أو حذفها قبل الاستخدام الرسمي.

---

## المتغيرات البيئية

يتم تحميل المتغيرات تلقائياً من ملف `.env` في جذر المشروع.

| المتغير | الوصف | القيمة الافتراضية |
|---------|-------|--------------------|
| `SECRET_KEY` | مفتاح تشفير جلسات Flask | قيمة غير آمنة — **إلزامي تغييره في الإنتاج** |
| `FLASK_DEBUG` | وضع التصحيح (`1` = مفعّل، `0` = معطّل) | `1` |
| `HOST` | عنوان IP للاستماع | `0.0.0.0` |
| `PORT` | رقم المنفذ | `5000` |
| `SESSION_COOKIE_SECURE` | تفعيل كوكيز آمنة عبر HTTPS (`1` أو `0`) | `0` |
| `DATABASE` | مسار ملف قاعدة البيانات | `db.sqlite3` |
| `UPLOAD_FOLDER` | مجلد حفظ إجابات الطلاب | `submissions` |
| `QUESTION_IMG_FOLDER` | مجلد صور الأسئلة | `question_images` |

---

## هيكل المشروع

```
E-Assessment System/
│
├── app.py                   # نقطة الدخول — وضع التطوير
├── run_production.py        # خادم الإنتاج (Waitress)
├── wsgi.py                  # واجهة WSGI للنشر خلف Nginx/Apache
├── config.py                # إعدادات التطبيق والمتغيرات البيئية
├── db.py                    # اتصال قاعدة البيانات SQLite
├── decorators.py            # حماية المسارات (تسجيل الدخول / الأدوار)
├── utils.py                 # دوال مساعدة مشتركة
├── mcq.py                   # منطق أسئلة الاختيار من متعدد (MCQ)
├── file_access.py           # التحكم في الوصول للملفات المحمية
├── requirements.txt         # قائمة الحزم المطلوبة
├── .env.example             # نموذج متغيرات البيئة
│
├── routes/                  # مسارات التطبيق (Blueprints)
│   ├── auth.py              # تسجيل الدخول والخروج والتوجيه
│   ├── instructor.py        # إدارة الاختبارات والأسئلة والتصحيح
│   ├── student.py           # عرض الاختبارات ورفع الإجابات
│   ├── admin.py             # إدارة المستخدمين (مدير النظام)
│   ├── courses.py           # إدارة المقررات والتسجيل
│   └── files.py             # تحميل الملفات المحمية
│
├── templates/               # قوالب HTML (Jinja2)
│   ├── base.html            # القالب الأساسي المشترك
│   ├── login.html           # صفحة تسجيل الدخول
│   ├── instructor_dashboard.html
│   ├── student_dashboard.html
│   ├── admin_dashboard.html
│   ├── create_exam.html
│   ├── add_questions.html
│   ├── submit_exam.html
│   ├── view_submissions.html
│   ├── student_result.html
│   ├── course_detail.html
│   └── ...
│
├── scripts/
│   ├── init_db.py           # تهيئة قاعدة البيانات من الصفر
│   └── migrate_db.py        # ترقية قاعدة بيانات موجودة
│
├── static/                  # ملفات ثابتة (CSS، JS، صور)
├── submissions/             # ملفات إجابات الطلاب (محمية)
└── question_images/         # صور الأسئلة المرفوعة
```

---

## قاعدة البيانات

يستخدم النظام **SQLite** مع تفعيل المفاتيح الخارجية (Foreign Keys).

### الجداول الرئيسية

| الجدول | الوصف |
|--------|--------|
| `users` | المستخدمون (طلاب، محاضرون، مشرفون) |
| `courses` | المقررات الدراسية |
| `enrollments` | تسجيل الطلاب في المقررات |
| `exams` | الاختبارات مع الجدول الزمني والمدة |
| `questions` | أسئلة الاختبارات (ملف / MCQ) |
| `submissions` | إجابات الطلاب المرفوعة والدرجات |
| `mcq_answers` | إجابات الطلاب على أسئلة الاختيار من متعدد |

---

## الميزات

### 👨‍🏫 المحاضر
- إنشاء وإدارة المقررات الدراسية
- إنشاء اختبارات وربطها بمقرر معين
- **جدولة الاختبارات تلقائياً** بتحديد وقت بدء مسبق
- إضافة أسئلة بصيغتين:
  - **ملف:** رفع ورقة أسئلة مع صورة اختيارية
  - **MCQ:** أسئلة اختيار من متعدد مع تصحيح تلقائي فوري
- بدء الاختبار يدوياً مع تحديد مدة الاختبار بالدقائق
- إنهاء الاختبار في أي وقت
- مراجعة إجابات الطلاب وإعطاء درجات وتعليقات
- **تصدير تقرير الدرجات كملف PDF**
- استيراد قائمة الطلاب عبر ملف CSV

### 👨‍🎓 الطالب
- عرض الاختبارات المتاحة المرتبطة بمقرراته
- **مؤقت عدّ تنازلي** يظهر الوقت المتبقي أثناء الاختبار
- رفع ملف الإجابة مع التحقق من الامتداد المسموح
- الإجابة على أسئلة MCQ مباشرة في الواجهة
- **عرض الدرجة والتعليقات** بعد التصحيح

### 🔧 مدير النظام
- إنشاء حسابات المستخدمين وتعديلها وحذفها
- تعيين دور كل مستخدم (طالب / محاضر / مدير)

---

## حسابات تجريبية

> هذه الحسابات للتطوير والاختبار فقط — **لا تستخدمها في الإنتاج**.

| المستخدم | كلمة المرور | الدور |
|----------|-------------|-------|
| `instructor1` | `1234` | محاضر |
| `student1` | `1234` | طالب |
| `admin1` | `admin123` | مدير النظام |

يتم إنشاء هذه الحسابات تلقائياً عند تشغيل `scripts/init_db.py`.

---

## استيراد الطلاب عبر CSV

يمكن للمحاضر استيراد قائمة طلاب دفعةً واحدة عبر ملف CSV بالتنسيق التالي:

```csv
username,full_name,password
student2,Ahmed Ali,1234
student3,Sara Hassan,secure_pass
student4,Mohammed Omar,
```

**القواعد:**
- عمود `username` **إلزامي** ويجب أن يكون فريداً.
- عمود `full_name` اختياري.
- إذا تُرك `password` فارغاً، يُستخدم كلمة المرور الافتراضية المحددة في نموذج الاستيراد.

---

## الأمان

| الميزة | التفاصيل |
|--------|----------|
| **تشفير كلمات المرور** | يستخدم `werkzeug.security` لتشفير وتحقق كلمات المرور (PBKDF2-SHA256) |
| **حماية CSRF** | تفعيل `Flask-WTF CSRFProtect` على جميع النماذج |
| **استعلامات آمنة** | استخدام Parameterized Queries لمنع SQL Injection |
| **حماية الملفات** | حظر الوصول المباشر لمسار `/static/uploads/` عبر `before_request` |
| **صلاحيات الأدوار** | فصل كامل بين صلاحيات المحاضر والطالب والمدير عبر Decorators |
| **Cookie Flags** | `HttpOnly=True`، `SameSite=Lax`، دعم `Secure` عبر HTTPS |
| **التحقق من الامتدادات** | قائمة بيضاء للملفات المسموح برفعها من الطلاب |

---

## النشر على GitHub

المشروع جاهز للنشر. الملفات التالية **لا تُرفع** تلقائياً (مُضافة لـ `.gitignore`):
- مجلد `.venv/`
- قاعدة البيانات `db.sqlite3`
- ملف الإعدادات السرية `.env`
- ملفات الطلاب في `submissions/`

```bash
git init
git add .
git commit -m "Initial commit: E-Assessment System"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/e-assessment-system.git
git push -u origin main
```


---

## 📄 الترخيص

هذا المشروع مرخص بموجب [MIT License](LICENSE).

