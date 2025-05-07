#!/usr/bin/env python3
"""
حزمة بوت الدراسة والتحفيز
"""

import os
import sys
from flask import Flask
import threading

from study_bot.config import logger
from study_bot.models import setup_db
from study_bot.bot import run_bot
from study_bot.scheduler import init_scheduler

def create_app():
    """إنشاء تطبيق بوت الدراسة والتحفيز"""
    from study_bot.web import create_app as create_web_app
    from study_bot.config import BOT_ENABLED
    
    # إنشاء تطبيق فلاسك
    app = create_web_app()
    
    # تهيئة قاعدة البيانات
    setup_db(app)
    
    # تهيئة المجدول
    scheduler = init_scheduler(app)
    
    # تشغيل البوت في خيط منفصل إذا كان مفعلاً
    if BOT_ENABLED:
        bot_thread = run_bot(app, in_thread=True)
    else:
        logger.warning("البوت معطل. سيتم تشغيل الواجهة الويب فقط.")
        bot_thread = None
    
    # بدء المجدول
    scheduler.start()
    
    # تسجيل وظيفة التنظيف عند إيقاف التطبيق
    @app.teardown_appcontext
    def cleanup(exception=None):
        """تنظيف الموارد عند إيقاف التطبيق"""
        logger.info("تنظيف الموارد...")
        scheduler.stop()
    
    logger.info("تم إنشاء وتهيئة التطبيق بنجاح")
    return app
