#!/usr/bin/env python3
"""
مجدول المهام
يحتوي على وظائف لجدولة المهام وإرسال الإشعارات
"""

import os
import threading
import time
import logging
from datetime import datetime, timedelta
import random

import flask
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from study_bot.config import logger, get_current_time, get_timezone_object
from study_bot.models import db, User, Group, GroupScheduleTracker, UserActivityLog, SystemStats
from study_bot.bot import send_message
from study_bot.scheduler_group_tasks import (
    schedule_group_morning_message,
    schedule_group_evening_message,
    send_group_motivation_messages,
    generate_group_daily_report,
    reset_group_daily_stats
)

# المتغيرات العامة
_scheduler = None
_scheduler_thread = None
_scheduler_running = False

# تعريف المنطقة الزمنية
# استخدام وظيفة get_timezone_object بدلاً من تعريف متغير جديد
# تجنب استخدام zoneinfo

# جدول المهام والتكرار
SCHEDULER_TASKS = [
    {
        'id': 'check_camp_tasks',
        'func': lambda: reset_group_daily_stats(),
        'trigger': 'interval',
        'minutes': 10
    },
    {
        'id': 'send_camp_reports',
        'func': lambda: generate_group_daily_report(),
        'trigger': 'interval',
        'hours': 3
    },
    {
        'id': 'send_motivational_messages',
        'func': lambda: send_group_motivation_messages(),
        'trigger': 'interval',
        'hours': 1
    },
    {
        'id': 'update_system_stats',
        'func': lambda: update_system_stats(),
        'trigger': 'interval',
        'minutes': 30
    },
    {
        'id': 'reset_daily_stats',
        'func': lambda: reset_daily_stats(),
        'trigger': 'cron',
        'hour': 0,
        'minute': 5
    }
]

def update_system_stats():
    """تحديث إحصائيات النظام"""
    try:
        # الحصول على الوقت الحالي
        now = get_current_time()
        
        # إنشاء أو تحديث إحصائيات النظام
        stats = SystemStats.get_or_create_for_today()
        
        # تحديث عدد المستخدمين النشطين
        stats.active_users_count = User.query.filter_by(is_active=True).count()
        
        # تحديث عدد المجموعات النشطة
        stats.active_groups_count = Group.query.filter_by(is_active=True).count()
        
        # تحديث إجمالي عدد الرسائل المرسلة
        # حساب مجموع الرسائل المرسلة من جميع المستخدمين
        total_messages_sent = db.session.query(db.func.sum(User.total_messages_sent)).scalar() or 0
        stats.total_messages_sent = total_messages_sent
        
        # تحديث إجمالي عدد المهام المكتملة
        # حساب مجموع المهام المكتملة من جميع المستخدمين
        total_tasks_completed = db.session.query(db.func.sum(User.total_tasks_completed)).scalar() or 0
        stats.total_tasks_completed = total_tasks_completed
        
        # حفظ التغييرات
        db.session.commit()
        
        logger.info(f"تم تحديث إحصائيات النظام في {now}")
        return True
    except Exception as e:
        logger.error(f"خطأ في تحديث إحصائيات النظام: {e}")
        return False


def reset_daily_stats():
    """إعادة تعيين الإحصائيات اليومية"""
    try:
        today = get_current_time().date()
        yesterday = today - timedelta(days=1)
        
        # إعادة تعيين سجلات النشاط التي تزيد عن 30 يوماً
        old_activity_logs = UserActivityLog.query.filter(UserActivityLog.date < (today - timedelta(days=30))).all()
        for activity in old_activity_logs:
            db.session.delete(activity)
        
        # تحديث سلاسل إنجاز المستخدمين
        users = User.query.filter_by(is_active=True).all()
        for user in users:
            # تحقق من آخر تحديث للسلسلة
            if user.last_streak_update:
                last_update = user.last_streak_update.date()
                
                # إذا كان آخر تحديث بالأمس، زيادة السلسلة
                if last_update == yesterday:
                    user.streak_days += 1
                    user.last_streak_update = get_current_time()
                # إذا كان آخر تحديث قبل الأمس، إعادة تعيين السلسلة
                elif last_update < yesterday:
                    user.streak_days = 0
                    user.streak_start_date = None
            
        db.session.commit()
        logger.info(f"تم إعادة تعيين الإحصائيات اليومية")
        return True
    except Exception as e:
        logger.error(f"خطأ في إعادة تعيين الإحصائيات اليومية: {e}")
        return False


def init_scheduler(app):
    """تهيئة المجدول"""
    global _scheduler, _scheduler_thread, _scheduler_running
    
    if _scheduler_running or _scheduler_thread and _scheduler_thread.is_alive():
        logger.warning("المجدول يعمل بالفعل")
        return
    
    # إنشاء المجدول مع منطقة زمنية محددة كسلسلة نصية بدلاً من كائن
    # يمكن لـ APScheduler التعامل مع سلاسل المناطق الزمنية مباشرة
    _scheduler = BackgroundScheduler(timezone='Africa/Cairo')
    
    # بدء تشغيل سلسلة المجدول
    _scheduler_running = True
    _scheduler_thread = threading.Thread(target=scheduler_thread_func, args=(app,))
    _scheduler_thread.daemon = True
    _scheduler_thread.start()
    
    logger.info("تم بدء تشغيل سلسلة المجدول")
    return _scheduler_thread


def scheduler_thread_func(app):
    """دالة سلسلة المجدول"""
    global _scheduler, _scheduler_running
    
    with app.app_context():
        logger.info("بدء حلقة المجدول")
        
        try:
            # بدء تشغيل المجدول
            _scheduler.start()
            
            # إضافة المهام
            for task in SCHEDULER_TASKS:
                # تحديد نوع الزناد
                if task['trigger'] == 'interval':
                    trigger_kwargs = {k: v for k, v in task.items() if k not in ['id', 'func', 'trigger']}
                    # إضافة المنطقة الزمنية المناسبة للمشغل
                    trigger = IntervalTrigger(timezone='Africa/Cairo', **trigger_kwargs)
                elif task['trigger'] == 'cron':
                    trigger_kwargs = {k: v for k, v in task.items() if k not in ['id', 'func', 'trigger']}
                    # إضافة المنطقة الزمنية المناسبة للمشغل
                    trigger = CronTrigger(timezone='Africa/Cairo', **trigger_kwargs)
                else:
                    logger.warning(f"نوع زناد غير معروف: {task['trigger']}")
                    continue
                
                # إضافة المهمة
                _scheduler.add_job(
                    task['func'],
                    trigger=trigger,
                    id=task['id']
                )
            
            logger.info("تم إضافة مهام المجدول")
            
            # التحقق من مهام المجموعات الصباحية والمسائية والمعسكرات
            reset_group_daily_stats()
            
            # الانتظار حتى يتم إيقاف المجدول
            while _scheduler_running:
                time.sleep(1)
                
        except Exception as e:
            logger.error(f"حدث خطأ في سلسلة المجدول: {e}")
        finally:
            if _scheduler and _scheduler.running:
                _scheduler.shutdown()
            _scheduler_running = False
            logger.info("تم إنهاء حلقة المجدول")


def shutdown_scheduler():
    """إيقاف المجدول"""
    global _scheduler, _scheduler_running
    
    if not _scheduler_running:
        logger.warning("المجدول ليس قيد التشغيل")
        return False
    
    logger.info("إيقاف المجدول")
    _scheduler_running = False
    
    if _scheduler and _scheduler.running:
        _scheduler.shutdown()
    
    time.sleep(2)  # انتظار انتهاء المهام الجارية
    
    logger.info("تم إيقاف المجدول")
    return True