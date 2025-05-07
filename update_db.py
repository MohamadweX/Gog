#!/usr/bin/env python3
"""
سكريبت لتحديث مخطط قاعدة البيانات
"""

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
db = SQLAlchemy(app)

def update_group_table():
    """تحديث جدول المجموعة بإضافة أعمدة جديدة"""
    with app.app_context():
        # إضافة الأعمدة الجديدة
        db.session.execute(text("ALTER TABLE \"group\" ADD COLUMN IF NOT EXISTS morning_schedule_enabled BOOLEAN DEFAULT FALSE"))
        db.session.execute(text("ALTER TABLE \"group\" ADD COLUMN IF NOT EXISTS evening_schedule_enabled BOOLEAN DEFAULT FALSE"))
        db.session.execute(text("ALTER TABLE \"group\" ADD COLUMN IF NOT EXISTS custom_schedule_enabled BOOLEAN DEFAULT FALSE"))
        db.session.execute(text("ALTER TABLE \"group\" ADD COLUMN IF NOT EXISTS setup_complete BOOLEAN DEFAULT FALSE"))
        db.session.execute(text("ALTER TABLE \"group\" ADD COLUMN IF NOT EXISTS setup_in_progress BOOLEAN DEFAULT FALSE"))
        db.session.execute(text("ALTER TABLE \"group\" ADD COLUMN IF NOT EXISTS setup_stage VARCHAR(50) DEFAULT 'not_started'"))
        db.session.commit()
        print("تم تحديث جدول المجموعة بنجاح!")

def update_group_participant_table():
    """تحديث جدول مشاركي المجموعة بإضافة أعمدة جديدة"""
    with app.app_context():
        # إضافة الأعمدة الجديدة
        db.session.execute(text("ALTER TABLE group_participant ADD COLUMN IF NOT EXISTS joined_morning BOOLEAN DEFAULT FALSE"))
        db.session.execute(text("ALTER TABLE group_participant ADD COLUMN IF NOT EXISTS joined_evening BOOLEAN DEFAULT FALSE"))
        db.session.execute(text("ALTER TABLE group_participant ADD COLUMN IF NOT EXISTS morning_day_streak INTEGER DEFAULT 0"))
        db.session.execute(text("ALTER TABLE group_participant ADD COLUMN IF NOT EXISTS evening_day_streak INTEGER DEFAULT 0"))
        db.session.execute(text("ALTER TABLE group_participant ADD COLUMN IF NOT EXISTS morning_points INTEGER DEFAULT 0"))
        db.session.execute(text("ALTER TABLE group_participant ADD COLUMN IF NOT EXISTS evening_points INTEGER DEFAULT 0"))
        db.session.execute(text("ALTER TABLE group_participant ADD COLUMN IF NOT EXISTS total_points INTEGER DEFAULT 0"))
        db.session.execute(text("ALTER TABLE group_participant ADD COLUMN IF NOT EXISTS daily_points INTEGER DEFAULT 0"))
        db.session.commit()
        print("تم تحديث جدول مشاركي المجموعة بنجاح!")


def create_new_task_tables():
    """إنشاء جداول المهام الجديدة"""
    with app.app_context():
        # إنشاء الجداول الجديدة
        try:
            # إضافة العلاقة إلى جدول GroupScheduleTracker
            from study_bot.models import GroupTaskTracker, GroupTaskParticipant
            
            # إنشاء الجداول
            db.create_all()
            print("تم إنشاء جداول المهام الجديدة بنجاح!")
        except Exception as e:
            print(f"حدث خطأ أثناء إنشاء الجداول الجديدة: {e}")

def update_group_schedule_tracker_table():
    """تحديث جدول تتبع جداول المجموعة بإضافة الأعمدة المفقودة"""
    with app.app_context():
        try:
            # إضافة الأعمدة المفقودة
            db.session.execute(text("ALTER TABLE group_schedule_tracker ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE"))
            db.session.execute(text("ALTER TABLE group_schedule_tracker ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW()"))
            db.session.execute(text("ALTER TABLE group_schedule_tracker ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW()"))
            db.session.execute(text("ALTER TABLE group_schedule_tracker ADD COLUMN IF NOT EXISTS start_date TIMESTAMP"))
            db.session.execute(text("ALTER TABLE group_schedule_tracker ADD COLUMN IF NOT EXISTS end_date TIMESTAMP"))
            db.session.execute(text("ALTER TABLE group_schedule_tracker ADD COLUMN IF NOT EXISTS settings JSONB"))
            db.session.commit()
            print("تم تحديث جدول تتبع جداول المجموعة بنجاح!")
        except Exception as e:
            print(f"حدث خطأ أثناء تحديث جدول تتبع جداول المجموعة: {e}")

if __name__ == "__main__":
    update_group_table()
    update_group_participant_table()
    create_new_task_tables()
    update_group_schedule_tracker_table()
    print("تم تحديث مخطط قاعدة البيانات بنجاح!")
