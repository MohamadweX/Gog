"""
ملف إعدادات مكتبة بوت الدراسة والتحفيز
يحتوي على ثوابت وإعدادات واستيراد متغيرات البيئة
"""

import os
import logging
import pytz

# إعداد السجل Logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("study_bot.log")
    ]
)

logger = logging.getLogger("study_bot")

# المنطقة الزمنية - استخدم UTC افتراضياً ثم قم بالتحويل عند العرض
TIMEZONE = pytz.timezone('Asia/Riyadh')  # المنطقة الزمنية للسعودية

# إعدادات تيليجرام
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_API_URL = "https://api.telegram.org/bot"

# إعدادات قاعدة البيانات
DATABASE_URL = os.environ.get("DATABASE_URL")

# إعدادات المجدول
SCHEDULER_INTERVAL = 60  # فترة تحقق المجدول بالثواني
DEFAULT_MISFIRE_GRACE_TIME = 60  # الفترة السماحية للمهام الفائتة بالثواني

# إعدادات خادم الويب
WEB_HOST = "0.0.0.0"
WEB_PORT = int(os.environ.get("PORT", 5000))
SECRET_KEY = os.environ.get("SESSION_SECRET", "super_secret_key_for_study_bot")
DEBUG_MODE = os.environ.get("DEBUG", "False").lower() == "true"

# المشرفين
ADMIN_IDS = [
    int(id_str) for id_str in os.environ.get("ADMIN_IDS", "").split(",") 
    if id_str.strip().isdigit()
]

def validate_config():
    """التحقق من إعدادات التهيئة"""
    errors = []
    
    if not TELEGRAM_BOT_TOKEN:
        errors.append("TELEGRAM_BOT_TOKEN غير موجود في متغيرات البيئة")
    
    if not DATABASE_URL:
        errors.append("DATABASE_URL غير موجود في متغيرات البيئة")
    
    if errors:
        for error in errors:
            logger.error(error)
        return False
    
    logger.info("تم التحقق من إعدادات التهيئة بنجاح")
    return True