"""
ملف الإعدادات للتطبيق
يحتوي على متغيرات الإعدادات والثوابت
"""

import os
import logging
import pytz
from datetime import datetime, timedelta

# إعداد التسجيل
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('study_bot')

# إعدادات تيليجرام
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
# عنوان API تيليجرام بدون توكن
TELEGRAM_API_URL = "https://api.telegram.org"
# اسم المستخدم للبوت
TELEGRAM_BOT_USERNAME = "Study_schedule501_bot"

# إعدادات المناطق الزمنية - تم تعديلها للتوقيت المصري الصيفي
SCHEDULER_TIMEZONE = pytz.timezone('Africa/Cairo')
DEFAULT_TIMEZONE = 'Africa/Cairo'

# وظائف مساعدة للتعامل مع التواريخ والأوقات
def get_current_time():
    """الحصول على الوقت الحالي بالمنطقة الزمنية المحددة"""
    # استخدام pytz بدلاً من zoneinfo للتوافق مع APScheduler
    # pytz يحتاج إلى طريقة خاصة للتعامل مع المناطق الزمنية
    now = datetime.now()
    if now.tzinfo is not None:
        now = now.replace(tzinfo=None)  # إزالة أي منطقة زمنية إذا كانت موجودة
    # استخدام localize بدلاً من replace للتوافق مع pytz
    return SCHEDULER_TIMEZONE.localize(now, is_dst=None)

def get_timezone_object():
    """الحصول على كائن المنطقة الزمنية"""
    # استخدام pytz للتوافق مع APScheduler
    # هذه الدالة تُستخدم عندما نحتاج إلى كائن منطقة زمنية وليس وقتًا بمنطقة زمنية
    return SCHEDULER_TIMEZONE

# إعدادات المجدول
SCHEDULER_INTERVAL = 5  # بالثواني

# الرسائل التحفيزية
MOTIVATIONAL_MESSAGES = [
    "النجاح هو محصلة جهد يومي متراكم",
    "العلم كالشجرة، يحتاج إلى رعاية مستمرة لينمو",
    "المثابرة هي سر التفوق",
    "ليس المهم كم تقرأ، بل كم تفهم وتطبق",
    "اجعل من التعلم عادة يومية",
    "الخطوة الأولى نحو النجاح هي الإيمان بقدرتك على تحقيقه",
    "الفشل هو مجرد فرصة للبدء من جديد بطريقة أكثر ذكاءً",
    "التعلم المستمر هو مفتاح التطور الدائم",
    "الاستذكار بانتظام أفضل من الاستذكار المكثف قبل الامتحان",
    "حين تتوقف عن التعلم، تبدأ في التراجع"
]

# إعدادات النقاط
POINTS_CONFIG = {
    "morning": {
        "fajr_prayer": 5,
        "breakfast": 3,
        "daily_plan": 5,
        "first_study": 10,
        "short_break": 2,
        "back_to_study": 5,
        "dhuhr_prayer": 5,
        "after_prayer_study": 8,
        "nap_time": 3,
        "wake_up": 3,
        "asr_prayer": 5,
        "review_study": 8,
        "maghrib_prayer": 5,
        "isha_prayer": 5,
        "evaluation": 10
    },
    "evening": {
        "evening_plan": 5,
        "evening_study": 10,
        "dinner_break": 3,
        "maghrib_prayer": 5,
        "night_study": 8,
        "isha_prayer": 5,
        "long_break": 2,
        "night_evaluation": 10
    },
    "custom": {
        "default_points": 5
    }
}

# إعدادات أخرى
DEBUG_MODE = True
SECRET_KEY = os.environ.get('SECRET_KEY', 'default_secret_key_for_development')