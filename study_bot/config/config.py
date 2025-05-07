#!/usr/bin/env python3
"""
ملف التكوين
يحتوي على سص التكوين والضبط للبوت
"""

import os
import logging
from logging.handlers import RotatingFileHandler
import sys
from datetime import datetime

# متغيرات البيئة
DATABASE_URL = os.environ.get("DATABASE_URL", "")
SECRET_KEY = os.environ.get("SESSION_SECRET", os.urandom(24))

# إعداد المسجل
logger = logging.getLogger("config")
logger.setLevel(logging.INFO)

# إنشاء مجلد السجلات إذا لم يكن موجودًا
if not os.path.exists("logs"):
    os.makedirs("logs")

# تكوين مخرجات السجلات
log_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# إضافة مخرج إلى الملف
log_file_handler = RotatingFileHandler(
    "logs/app.log",
    maxBytes=1024 * 1024 * 5,  # 5 ميجابايت
    backupCount=5
)
log_file_handler.setFormatter(log_formatter)
logger.addHandler(log_file_handler)

# إضافة مخرج إلى وحدة التحكم
log_console_handler = logging.StreamHandler(sys.stdout)
log_console_handler.setFormatter(log_formatter)
logger.addHandler(log_console_handler)

# ثوابت API تيليغرام
TELEGRAM_API_URL = "https://api.telegram.org/bot"
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

# الإعدادات الافتراضية للجدول الصباحي
MORNING_SCHEDULE = {
    "start_time": "04:30",
    "end_time": "15:00",
    "join_time": "05:00",
    "prayer_1_time": "05:15",  # الفجر
    "meal_1_time": "05:30",    # الإفطار
    "study_1_time": "06:00",   # بدء المذاكرة
    "prayer_2_time": "12:00",  # الظهر
    "study_2_time": "12:30",   # مذاكرة بعد الظهر
    "return_time": "13:30",    # العودة بعد الراحة
    "prayer_3_time": "15:30",  # العصر
    "study_3_time": "16:00",   # المراجعة
    "prayer_4_time": "18:00",  # المغرب
    "prayer_5_time": "19:30",  # العشاء
    "evaluation_time": "21:00"  # تقييم اليوم
}

# الإعدادات الافتراضية للجدول المسائي
EVENING_SCHEDULE = {
    "start_time": "16:00",
    "end_time": "23:00",
    "join_time": "16:00",
    "study_1_time": "16:30",   # بدء المراجعة
    "prayer_1_time": "18:00",  # المغرب
    "study_2_time": "18:30",   # بدء واجب/تدريب
    "prayer_2_time": "19:30",  # العشاء
    "study_3_time": "20:00",   # الحفظ/القراءة
    "evaluation_time": "21:30", # تقييم اليوم
    "early_sleep_time": "22:30" # النوم المبكر
}

# نقاط الجدول الصباحي
MORNING_POINTS = {
    "join": 5,            # تسجيل الحضور
    "prayer_1": 5,        # الفجر
    "meal_1": 3,          # الإفطار
    "study_1": 10,        # بدء المذاكرة
    "prayer_2": 5,        # الظهر
    "study_2": 10,        # مذاكرة بعد الظهر
    "return_after_break": 5, # العودة بعد الراحة
    "prayer_3": 5,        # العصر
    "study_3": 10,        # المراجعة
    "prayer_4": 5,        # المغرب
    "prayer_5": 5,        # العشاء
    "evaluation": 7,      # تقييم اليوم
    "completion": 20      # إكمال الجدول كاملاً
}

# نقاط الجدول المسائي
EVENING_POINTS = {
    "join": 5,            # تسجيل الحضور
    "study_1": 10,        # بدء المراجعة
    "prayer_1": 5,        # المغرب
    "study_2": 10,        # بدء واجب/تدريب
    "prayer_2": 5,        # العشاء
    "study_3": 10,        # الحفظ/القراءة
    "evaluation": 7,      # تقييم اليوم
    "early_sleep": 8,     # النوم المبكر
    "completion": 15      # إكمال الجدول كاملاً
}

# إعدادات المعسكرات
DEFAULT_CAMP_DURATION = 14  # المدة الافتراضية للمعسكر بالأيام
DEFAULT_MORNING_SCHEDULE = MORNING_SCHEDULE  # الجدول الافتراضي للمعسكر الصباحي
DEFAULT_EVENING_SCHEDULE = EVENING_SCHEDULE  # الجدول الافتراضي للمعسكر المسائي

# إعدادات الويب
WEB_HOST = "0.0.0.0"  # مضيف واجهة الويب
WEB_PORT = 5000  # منفذ واجهة الويب
DEBUG_MODE = True  # وضع التصحيح

# إعدادات المجدول الزمني
SCHEDULER_INTERVAL = 60  # الفاصل الزمني للمجدول بالثواني

def validate_config():
    """التحقق من صحة الإعدادات وتوفر المتطلبات الأساسية"""
    # التحقق من توفر توكن البوت
    global TELEGRAM_BOT_TOKEN
    TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("توكن البوت غير موجود! سيتم تشغيل واجهة الويب فقط دون وظائف البوت")
        return False
    
    # التحقق من اتصال قاعدة البيانات
    global DATABASE_URL
    DATABASE_URL = os.environ.get("DATABASE_URL")
    if not DATABASE_URL:
        logger.error("رابط قاعدة البيانات غير موجود! لا يمكن تشغيل التطبيق")
        return False
    
    logger.info("تم التحقق من صحة الإعدادات بنجاح")
    return True

# تنفيذ وظيفة التحقق عند استيراد الملف
config_valid = validate_config()
