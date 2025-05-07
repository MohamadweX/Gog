"""
حزمة بوت الدراسة والتحفيز
"""

import os
import logging
import sys
from datetime import datetime, timedelta
import threading
import functools
from flask import Flask

from study_bot.config import logger, SCHEDULER_TIMEZONE, TELEGRAM_BOT_TOKEN
from study_bot.models import init_db

def create_app():
    """إنشاء تطبيق بوت الدراسة والتحفيز"""
    # إنشاء تطبيق فلاسك
    app = Flask(__name__)
    
    # تكوين قاعدة البيانات
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_key')
    
    # في حال عدم وجود معرف للبوت، إيقاف العملية
    if not TELEGRAM_BOT_TOKEN:
        logger.error("رمز البوت غير موجود. تأكد من تعيين TELEGRAM_BOT_TOKEN")
        return app
    
    # تهيئة قاعدة البيانات
    db = init_db(app)
    
    # تهيئة نظام التسجيل المفصل
    os.makedirs('logs', exist_ok=True)
    
    # تهيئة البوت
    from study_bot.bot import init_bot
    bot = init_bot(app)
    
    # تهيئة المجدولات
    from study_bot.scheduler import init_scheduler
    scheduler_thread = init_scheduler(app)
    
    # جدولة إرسال رسالة تحفيزية بعد دقيقة من التفعيل
    from study_bot.auto_motivator import schedule_activation_motivation
    motivation_thread = schedule_activation_motivation()
    
    # تهيئة واجهة الويب
    from study_bot.web import init_web
    init_web(app)
    
    # إضافة دالة للتنظيف عند اغلاق التطبيق (وليس أثناء سياق HTTP)
    import atexit
    
    def cleanup_resources():
        """تنظيف الموارد عند إيقاف التطبيق"""
        logger.info("إيقاف التطبيق وتنظيف الموارد")
        
        # إيقاف البوت بشكل آمن
        try:
            from study_bot.bot import stop_bot
            stop_bot()
        except Exception as e:
            logger.error(f"خطأ أثناء إيقاف البوت: {e}")
            
        # إيقاف المجدول بشكل آمن
        try:
            from study_bot.scheduler import shutdown_scheduler
            shutdown_scheduler()
        except Exception as e:
            logger.error(f"خطأ أثناء إيقاف المجدول: {e}")
    
    # تسجيل دالة التنظيف ليتم استدعاؤها عند إيقاف التطبيق
    atexit.register(cleanup_resources)
    
    return app