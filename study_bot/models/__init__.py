"""
وحدة قاعدة البيانات الرئيسية
تحتوي على تهيئة ORM وتحميل النماذج
"""

import os
import json
import logging
from datetime import datetime, timedelta
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

from study_bot.config import logger, SCHEDULER_TIMEZONE

# تعريف قاعدة البيانات
class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# النماذج المستوردة
from study_bot.models.user import User, UserActivityLog
from study_bot.models.group import (
    Group, GroupScheduleTracker, GroupTaskTracker,
    GroupTaskParticipant, GroupTaskParticipation, MotivationalMessage
)
from study_bot.models.stats import SystemStats, DailyStats
from study_bot.models.camps import (
    CustomCamp, CampTask, CampParticipant, CampTaskParticipation
)

# نموذج سجل رسائل
class MessageLog(db.Model):
    """نموذج سجل الرسائل"""
    __tablename__ = 'message_log'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.BigInteger, nullable=True)  # تغيير من Integer إلى BigInteger لدعم معرفات تيليجرام الكبيرة
    chat_id = db.Column(db.BigInteger, nullable=False)
    message_id = db.Column(db.Integer, nullable=True)
    message_type = db.Column(db.String(50), nullable=False)  # send, receive, edit, delete
    content = db.Column(db.Text, nullable=True)  # محتوى الرسالة (النص أو وصف للمحتوى الآخر)
    is_from_bot = db.Column(db.Boolean, default=False)  # هل الرسالة من البوت
    sent_at = db.Column(db.DateTime, default=datetime.now(SCHEDULER_TIMEZONE))

def init_db(app):
    """تهيئة قاعدة البيانات"""
    db.init_app(app)
    
    with app.app_context():
        # إنشاء كافة الجداول
        db.create_all()
        
        # زيادة عداد بدء التشغيل
        try:
            startup_count = SystemStats.get_value("startup_count", 0)
            if startup_count is None:
                startup_count = 0
            SystemStats.set_value("startup_count", startup_count + 1)
        except Exception as e:
            logger.error(f"خطأ في زيادة عداد بدء التشغيل: {e}")
    
    logger.info("تم تهيئة قاعدة البيانات")
    return db