#!/usr/bin/env python3
"""
ملف الإعدادات للبوت وواجهة الويب
يحتوي على إعدادات الاتصال، والمتغيرات البيئية، والإعدادات الأخرى
"""

import os
import logging
import sys

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("study_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# معلومات البوت
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "dummy_token_for_web_only")
if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "dummy_token_for_web_only":
    logger.warning("توكن البوت غير موجود! سيتم تشغيل واجهة الويب فقط دون وظائف البوت")
    BOT_ENABLED = False
else:
    BOT_ENABLED = True

# عنوان API تيليجرام
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# إعدادات قاعدة البيانات
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    logger.warning("DATABASE_URL غير موجود! استخدام قاعدة بيانات محلية")
    # استخدام قاعدة بيانات SQLite محلية كبديل
    DATABASE_URL = "sqlite:///studybot.db"

# إعدادات خادم الويب
WEB_HOST = "0.0.0.0"
WEB_PORT = 5000
DEBUG_MODE = os.environ.get("DEBUG_MODE", "True").lower() in ("true", "1", "t", "yes")

# مفتاح السر للجلسات
SECRET_KEY = os.environ.get("SESSION_SECRET", "super_secret_key_change_in_production")

# إعدادات المجدول
SCHEDULER_INTERVAL = 60  # الفاصل الزمني للمجدول بالثواني

# إعدادات النقاط للجدول الصباحي
MORNING_POINTS = {
    "join": 5,         # الانضمام للمعسكر
    "prayer_1": 5,     # صلاة الفجر
    "meal_1": 2,       # الإفطار
    "study_1": 7,      # بدء المذاكرة
    "prayer_2": 3,     # صلاة الظهر
    "study_2": 6,      # المذاكرة بعد الظهر
    "rest": 1,         # العودة بعد الراحة
    "prayer_3": 3,     # صلاة العصر
    "study_3": 6,      # المراجعة
    "prayer_4": 2,     # صلاة المغرب
    "prayer_5": 2,     # صلاة العشاء
    "evaluation": 5,   # تقييم اليوم
    "complete_day": 3  # إكمال اليوم بالكامل
}

# إعدادات النقاط للجدول المسائي
EVENING_POINTS = {
    "join": 5,         # الانضمام للجدول المسائي
    "study_1": 6,      # بدء المراجعة
    "prayer_1": 2,     # صلاة المغرب
    "study_2": 6,      # بدء واجب أو تدريب
    "prayer_2": 2,     # صلاة العشاء
    "study_3": 5,      # الحفظ أو القراءة الخفيفة
    "evaluation": 4,   # تقييم اليوم المسائي
    "early_sleep": 5,  # النوم المبكر (تعهد)
    "complete_day": 5  # إكمال كل المهام
}

# إعدادات النقاط العامة (للقديم)
POINTS_CONFIG = {
    "prayer": 3,      # نقاط الصلاة
    "study": 6,       # نقاط المذاكرة
    "meal": 2,        # نقاط الوجبات
    "evaluation": 5,  # نقاط تقييم اليوم
    "join": 5         # نقاط الانضمام
}

# التحقق من صحة الإعدادات
def validate_config():
    """التحقق من صحة الإعدادات وتوفر المتطلبات الأساسية"""
    warnings = []
    
    # التحقق من وجود توكن البوت
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "dummy_token_for_web_only":
        warnings.append("توكن البوت غير موجود - سيتم تشغيل واجهة الويب فقط")
    
    # التحقق من صحة الاتصال بقاعدة البيانات
    if not DATABASE_URL:
        warnings.append("متغير DATABASE_URL غير محدد - سيتم استخدام قاعدة بيانات محلية")
    
    # إظهار التحذيرات إن وجدت
    for warning in warnings:
        logger.warning(f"تحذير: {warning}")
    
    # لن نتوقف عن تشغيل التطبيق بسبب التحذيرات
    return True
