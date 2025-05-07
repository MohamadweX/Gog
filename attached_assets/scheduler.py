#!/usr/bin/env python3
"""
وحدة المجدول
تحتوي على وظائف جدولة المهام والتذكيرات
"""

import os
import sys
import uuid
import random
from datetime import datetime, timedelta
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

# استيراد الإعدادات
from study_bot.config import SCHEDULER_INTERVAL, logger
from study_bot.models import User, ScheduleTracker, UserActivity, db, NotificationPreference, SystemStat
from study_bot.bot import send_message
from threading import Timer

# استيراد المهام الخاصة بالمجموعات
from study_bot.scheduler_group_tasks import (
    schedule_group_morning_message,
    schedule_group_evening_message,
    send_group_motivation_messages,
    generate_group_daily_report,
    reset_group_daily_stats
)

# استيراد مهام المعسكرات الدراسية
from study_bot.camp_scheduler import (
    check_and_send_scheduled_camp_tasks,
    generate_camp_daily_report
)

# إنشاء متغير عمومي للمجدول
_scheduler = None

# قاموس لتخزين المؤقتات
activation_timers = {}

def schedule_activation_confirmation(app, chat_id, is_group=False, user_id=None):
    """جدولة رسالة تأكيد بعد دقيقتين من التفعيل"""
    try:
        # إنشاء معرف فريد للمؤقت
        timer_id = str(uuid.uuid4())
        
        def send_confirmation_message():
            with app.app_context():
                try:
                    # إختيار رسالة تحفيزية عشوائية
                    from study_bot.group_tasks import MOTIVATIONAL_QUOTES
                    quote = random.choice(MOTIVATIONAL_QUOTES)
                    
                    # إضافة نص التأكيد
                    confirmation_message = f"✅ <b>تأكيد التفعيل</b>\n\nتم تفعيل بوت الدراسة والتحفيز بنجاح.\n\n{quote}\n\n<i>فريق المطورين - @M_o_h_a_m_e_d_501</i>"
                    
                    # إرسال الرسالة
                    send_message(chat_id, confirmation_message)
                    
                    logger.info(f"تم إرسال رسالة تأكيد التفعيل إلى {chat_id}")
                    
                    # إزالة المؤقت من القاموس
                    if timer_id in activation_timers:
                        del activation_timers[timer_id]
                except Exception as e:
                    logger.error(f"خطأ في إرسال رسالة تأكيد التفعيل: {e}")
        
        # إنشاء مؤقت لإرسال الرسالة بعد دقيقتين
        timer = Timer(120.0, send_confirmation_message)
        timer.daemon = True  # جعل المؤقت خلفي لإيقافه عند إيقاف التطبيق
        timer.start()
        
        # تخزين المؤقت للرجوع إليه لاحقًا
        activation_timers[timer_id] = timer
        
        logger.info(f"تم جدولة رسالة تأكيد التفعيل لـ {chat_id} بعد دقيقتين")
        return timer_id
    except Exception as e:
        logger.error(f"خطأ في جدولة رسالة تأكيد التفعيل: {e}")
        return None

def send_private_message_to_admin(app, group_id, admin_id):
    """إرسال رسالة للمشرف في الخاص بعد تفعيل البوت في مجموعة"""
    try:
        with app.app_context():
            from study_bot.models import Group, User
            
            # الحصول على معلومات المجموعة
            group = Group.query.filter_by(id=group_id).first()
            if not group:
                logger.error(f"لم يتم العثور على المجموعة بالمعرف {group_id}")
                return False
            
            # التحقق من وجود المستخدم
            user = User.query.filter_by(telegram_id=admin_id).first()
            if not user:
                # إنشاء مستخدم جديد إذا لم يكن موجودًا
                user = User.get_or_create(telegram_id=admin_id)
            
            # إرسال رسالة للمشرف في الخاص
            admin_message = f"""🛠️ <b>إدارة المجموعة</b>

مرحبًا! أنت الآن مشرف لمجموعة <b>{group.title}</b> في بوت الدراسة والتحفيز.\n
يمكنك إدارة المجموعة وإعداد المعسكرات الدراسية مباشرة من المحادثة الخاصة معي هنا.

استخدم الأوامر التالية:
/groups - لإدارة مجموعاتك
/camps - لإدارة معسكرات الدراسة
/help - لعرض قائمة الأوامر المتاحة

<i>فريق المطورين - @M_o_h_a_m_e_d_501</i>"""
            
            send_message(admin_id, admin_message)
            logger.info(f"تم إرسال رسالة خاصة للمشرف {admin_id} عن المجموعة {group.title}")
            return True
    except Exception as e:
        logger.error(f"خطأ في إرسال رسالة للمشرف في الخاص: {e}")
        return False

def init_scheduler(app):
    """تهيئة المجدول وإضافة المهام"""
    global _scheduler
    
    logger.info("تهيئة المجدول...")
    
    # إنشاء مجدول جديد إذا لم يكن موجوداً
    if _scheduler is None:
        _scheduler = BackgroundScheduler()
        
        # إضافة وظيفة الإيقاف
        def stop():
            """إيقاف المجدول"""
            if _scheduler.running:
                logger.info("إيقاف المجدول...")
                _scheduler.shutdown()
                
        # إضافة وظيفة الإيقاف كخاصية للمجدول
        _scheduler.stop = stop
    
    # إضافة المهام المجدولة
    
    # تذكير صلاة الفجر (5:00 صباحاً)
    _scheduler.add_job(
        scheduled_morning_prayer_reminder,
        CronTrigger(hour=5, minute=0),
        args=[app],
        id='morning_prayer_reminder',
        replace_existing=True
    )
    
    # تذكير بداية المعسكر الصباحي (7:00 صباحاً)
    _scheduler.add_job(
        scheduled_morning_camp_reminder,
        CronTrigger(hour=7, minute=0),
        args=[app],
        id='morning_camp_reminder',
        replace_existing=True
    )
    
    # تذكير صلاة الظهر (12:00 ظهراً)
    _scheduler.add_job(
        scheduled_dhuhr_prayer_reminder,
        CronTrigger(hour=12, minute=0),
        args=[app],
        id='dhuhr_prayer_reminder',
        replace_existing=True
    )
    
    # تذكير بداية المعسكر المسائي (3:00 عصراً)
    _scheduler.add_job(
        scheduled_evening_camp_reminder,
        CronTrigger(hour=15, minute=0),
        args=[app],
        id='evening_camp_reminder',
        replace_existing=True
    )
    
    # تذكير صلاة العصر (3:30 عصراً)
    _scheduler.add_job(
        scheduled_asr_prayer_reminder,
        CronTrigger(hour=15, minute=30),
        args=[app],
        id='asr_prayer_reminder',
        replace_existing=True
    )
    
    # تذكير صلاة المغرب (6:30 مساءً)
    _scheduler.add_job(
        scheduled_maghrib_prayer_reminder,
        CronTrigger(hour=18, minute=30),
        args=[app],
        id='maghrib_prayer_reminder',
        replace_existing=True
    )
    
    # تذكير صلاة العشاء (8:00 مساءً)
    _scheduler.add_job(
        scheduled_isha_prayer_reminder,
        CronTrigger(hour=20, minute=0),
        args=[app],
        id='isha_prayer_reminder',
        replace_existing=True
    )
    
    # تذكير تقييم اليوم (10:00 مساءً)
    _scheduler.add_job(
        scheduled_daily_evaluation_reminder,
        CronTrigger(hour=22, minute=0),
        args=[app],
        id='daily_evaluation_reminder',
        replace_existing=True
    )
    
    # تذكير النوم المبكر (11:00 مساءً)
    _scheduler.add_job(
        scheduled_early_sleep_reminder,
        CronTrigger(hour=23, minute=0),
        args=[app],
        id='early_sleep_reminder',
        replace_existing=True
    )
    
    # وظيفة التحقق من المهام المتبقية (كل ساعة)
    _scheduler.add_job(
        scheduled_check_remaining_tasks,
        IntervalTrigger(hours=1),
        args=[app],
        id='check_remaining_tasks',
        replace_existing=True
    )
    
    # تحديث إحصائيات النظام (منتصف الليل)
    _scheduler.add_job(
        scheduled_update_system_stats,
        CronTrigger(hour=0, minute=0),
        args=[app],
        id='update_system_stats',
        replace_existing=True
    )
    
    # إرسال رسائل تحفيزية (كل ساعة)
    _scheduler.add_job(
        scheduled_send_motivational_messages,
        IntervalTrigger(hours=1),
        args=[app],
        id='send_motivational_messages',
        replace_existing=True
    )
    
    # تعيين مجدول محسن الإشعارات الذكي (كل 15 دقيقة)
    _scheduler.add_job(
        scheduled_smart_notifications,
        IntervalTrigger(minutes=15),
        args=[app],
        id='smart_notifications',
        replace_existing=True
    )
    
    # إضافة مهام المجموعات
    
    # إرسال رسالة الجدول الصباحي للمجموعات (03:00 صباحاً)
    _scheduler.add_job(
        schedule_group_morning_message,
        CronTrigger(hour=3, minute=0),
        id='group_morning_schedule',
        replace_existing=True
    )
    
    # إرسال رسالة الجدول المسائي للمجموعات (16:00 مساءً)
    _scheduler.add_job(
        schedule_group_evening_message,
        CronTrigger(hour=16, minute=0),
        id='group_evening_schedule',
        replace_existing=True
    )
    
    # إرسال رسائل تحفيزية للمجموعات (كل ساعة)
    _scheduler.add_job(
        send_group_motivation_messages,
        IntervalTrigger(hours=1),
        id='group_motivation_messages',
        replace_existing=True
    )
    
    # إنشاء تقرير يومي للمجموعات (01:00 صباحاً)
    _scheduler.add_job(
        generate_group_daily_report,
        CronTrigger(hour=1, minute=0),
        id='group_daily_report',
        replace_existing=True
    )
    
    # إعادة تعيين إحصائيات المجموعات اليومية (02:00 صباحاً)
    _scheduler.add_job(
        reset_group_daily_stats,
        CronTrigger(hour=2, minute=0),
        id='reset_group_daily_stats',
        replace_existing=True
    )
    
    # إضافة مهام المعسكرات الدراسية
    
    # التحقق من وإرسال مهام المعسكرات المجدولة (كل دقيقتين)
    _scheduler.add_job(
        check_and_send_scheduled_camp_tasks,
        IntervalTrigger(minutes=2),
        id='check_camp_tasks',
        replace_existing=True
    )
    
    # إنشاء تقرير يومي للمعسكرات (11:00 مساءً)
    _scheduler.add_job(
        generate_camp_daily_report,
        CronTrigger(hour=23, minute=0),
        id='camp_daily_report',
        replace_existing=True
    )
    
    logger.info("تم إضافة جميع المهام المجدولة")
    
    return _scheduler

def scheduled_morning_prayer_reminder(app):
    """تذكير صلاة الفجر المجدول"""
    with app.app_context():
        current_time = datetime.utcnow()
        logger.info(f"تشغيل مذكر صلاة الفجر في {current_time}")
        
        # الحصول على المستخدمين النشطين بجدول صباحي
        users = User.query.filter_by(
            is_active=True,
            preferred_schedule='morning'
        ).all()
        
        for user in users:
            try:
                # تحقق إذا كان المستخدم قد سجل صلاة الفجر بالفعل
                tracker = ScheduleTracker.get_or_create_for_today(user.id, 'morning')
                if not tracker.prayer_1:
                    # إرسال تذكير
                    send_message(
                        user.telegram_id,
                        "🕌 <b>تذكير صلاة الفجر</b>\n\nحان موعد صلاة الفجر. صَلِّ لتبدأ يومك بالخير."
                    )
            except Exception as e:
                logger.error(f"خطأ في إرسال تذكير صلاة الفجر للمستخدم {user.id}: {e}")

def scheduled_morning_camp_reminder(app):
    """تذكير بداية المعسكر الصباحي"""
    with app.app_context():
        current_time = datetime.utcnow()
        logger.info(f"تشغيل مذكر بداية المعسكر الصباحي في {current_time}")
        
        # الحصول على المستخدمين النشطين بجدول صباحي
        users = User.query.filter_by(
            is_active=True,
            preferred_schedule='morning'
        ).all()
        
        for user in users:
            try:
                # تحقق إذا كان المستخدم قد سجل حضوره بالفعل
                tracker = ScheduleTracker.get_or_create_for_today(user.id, 'morning')
                if not tracker.joined:
                    # إرسال تذكير
                    send_message(
                        user.telegram_id,
                        "🌞 <b>تذكير المعسكر الصباحي</b>\n\nأهلاً بك في المعسكر الصباحي. لا تنس تسجيل حضورك وبدء مذاكرتك."
                    )
            except Exception as e:
                logger.error(f"خطأ في إرسال تذكير المعسكر الصباحي للمستخدم {user.id}: {e}")

def scheduled_dhuhr_prayer_reminder(app):
    """تذكير صلاة الظهر"""
    with app.app_context():
        current_time = datetime.utcnow()
        logger.info(f"تشغيل مذكر صلاة الظهر في {current_time}")
        
        # الحصول على جميع المستخدمين النشطين (صباحي أو مسائي)
        users = User.query.filter_by(is_active=True).filter(
            User.preferred_schedule.in_(['morning', 'custom'])
        ).all()
        
        for user in users:
            try:
                # تحقق إذا كان المستخدم قد سجل صلاة الظهر بالفعل
                tracker = ScheduleTracker.get_or_create_for_today(user.id, user.preferred_schedule)
                if not tracker.prayer_2:
                    # إرسال تذكير
                    send_message(
                        user.telegram_id,
                        "🕌 <b>تذكير صلاة الظهر</b>\n\nحان موعد صلاة الظهر. استرح قليلاً من المذاكرة لأداء الصلاة."
                    )
            except Exception as e:
                logger.error(f"خطأ في إرسال تذكير صلاة الظهر للمستخدم {user.id}: {e}")

def scheduled_evening_camp_reminder(app):
    """تذكير بداية المعسكر المسائي"""
    with app.app_context():
        current_time = datetime.utcnow()
        logger.info(f"تشغيل مذكر بداية المعسكر المسائي في {current_time}")
        
        # الحصول على المستخدمين النشطين بجدول مسائي
        users = User.query.filter_by(
            is_active=True,
            preferred_schedule='evening'
        ).all()
        
        for user in users:
            try:
                # تحقق إذا كان المستخدم قد سجل حضوره بالفعل
                tracker = ScheduleTracker.get_or_create_for_today(user.id, 'evening')
                if not tracker.joined:
                    # إرسال تذكير
                    send_message(
                        user.telegram_id,
                        "🌙 <b>تذكير المعسكر المسائي</b>\n\nأهلاً بك في المعسكر المسائي. لا تنس تسجيل حضورك وبدء مذاكرتك."
                    )
            except Exception as e:
                logger.error(f"خطأ في إرسال تذكير المعسكر المسائي للمستخدم {user.id}: {e}")

def scheduled_asr_prayer_reminder(app):
    """تذكير صلاة العصر"""
    with app.app_context():
        current_time = datetime.utcnow()
        logger.info(f"تشغيل مذكر صلاة العصر في {current_time}")
        
        # الحصول على جميع المستخدمين النشطين (صباحي أو مسائي)
        users = User.query.filter_by(is_active=True).filter(
            User.preferred_schedule.in_(['morning', 'evening', 'custom'])
        ).all()
        
        for user in users:
            try:
                # تحقق إذا كان المستخدم قد سجل صلاة العصر بالفعل
                tracker = ScheduleTracker.get_or_create_for_today(user.id, user.preferred_schedule)
                if not tracker.prayer_3 and user.preferred_schedule == 'morning':
                    # إرسال تذكير
                    send_message(
                        user.telegram_id,
                        "🕌 <b>تذكير صلاة العصر</b>\n\nحان موعد صلاة العصر. لا تنس أخذ استراحة من المذاكرة لأداء الصلاة."
                    )
            except Exception as e:
                logger.error(f"خطأ في إرسال تذكير صلاة العصر للمستخدم {user.id}: {e}")

def scheduled_maghrib_prayer_reminder(app):
    """تذكير صلاة المغرب"""
    with app.app_context():
        current_time = datetime.utcnow()
        logger.info(f"تشغيل مذكر صلاة المغرب في {current_time}")
        
        # الحصول على جميع المستخدمين النشطين
        users = User.query.filter_by(is_active=True).filter(
            User.preferred_schedule.in_(['morning', 'evening', 'custom'])
        ).all()
        
        for user in users:
            try:
                tracker = ScheduleTracker.get_or_create_for_today(user.id, user.preferred_schedule)
                
                # رسالة مختلفة حسب نوع الجدول
                if user.preferred_schedule == 'morning' and not tracker.prayer_4:
                    send_message(
                        user.telegram_id,
                        "🕌 <b>تذكير صلاة المغرب</b>\n\nحان موعد صلاة المغرب. لا تنس أخذ استراحة من المذاكرة لأداء الصلاة."
                    )
                elif user.preferred_schedule == 'evening' and not tracker.prayer_1:
                    send_message(
                        user.telegram_id,
                        "🕌 <b>تذكير صلاة المغرب</b>\n\nحان موعد صلاة المغرب. بعد الصلاة يمكنك البدء بمهام المراجعة المسائية."
                    )
            except Exception as e:
                logger.error(f"خطأ في إرسال تذكير صلاة المغرب للمستخدم {user.id}: {e}")

def scheduled_isha_prayer_reminder(app):
    """تذكير صلاة العشاء"""
    with app.app_context():
        current_time = datetime.utcnow()
        logger.info(f"تشغيل مذكر صلاة العشاء في {current_time}")
        
        # الحصول على جميع المستخدمين النشطين
        users = User.query.filter_by(is_active=True).filter(
            User.preferred_schedule.in_(['morning', 'evening', 'custom'])
        ).all()
        
        for user in users:
            try:
                tracker = ScheduleTracker.get_or_create_for_today(user.id, user.preferred_schedule)
                
                # رسالة مختلفة حسب نوع الجدول
                if user.preferred_schedule == 'morning' and not tracker.prayer_5:
                    send_message(
                        user.telegram_id,
                        "🕌 <b>تذكير صلاة العشاء</b>\n\nحان موعد صلاة العشاء. بعد الصلاة لا تنس تقييم يومك."
                    )
                elif user.preferred_schedule == 'evening' and not tracker.prayer_2:
                    send_message(
                        user.telegram_id,
                        "🕌 <b>تذكير صلاة العشاء</b>\n\nحان موعد صلاة العشاء. بعد الصلاة يمكنك متابعة مهام الحفظ والقراءة الخفيفة."
                    )
            except Exception as e:
                logger.error(f"خطأ في إرسال تذكير صلاة العشاء للمستخدم {user.id}: {e}")

def scheduled_daily_evaluation_reminder(app):
    """تذكير تقييم اليوم"""
    with app.app_context():
        current_time = datetime.utcnow()
        logger.info(f"تشغيل مذكر تقييم اليوم في {current_time}")
        
        # الحصول على جميع المستخدمين النشطين
        users = User.query.filter_by(is_active=True).filter(
            User.preferred_schedule.in_(['morning', 'evening', 'custom'])
        ).all()
        
        for user in users:
            try:
                tracker = ScheduleTracker.get_or_create_for_today(user.id, user.preferred_schedule)
                
                if not tracker.evaluation:
                    send_message(
                        user.telegram_id,
                        "📝 <b>تذكير تقييم اليوم</b>\n\nلا تنس تقييم إنجازاتك لهذا اليوم. سجل تقييمك باستخدام زر 'تقييم اليوم' في جدولك."
                    )
            except Exception as e:
                logger.error(f"خطأ في إرسال تذكير تقييم اليوم للمستخدم {user.id}: {e}")

def scheduled_early_sleep_reminder(app):
    """تذكير النوم المبكر"""
    with app.app_context():
        current_time = datetime.utcnow()
        logger.info(f"تشغيل مذكر النوم المبكر في {current_time}")
        
        # الحصول على المستخدمين النشطين بجدول مسائي
        users = User.query.filter_by(
            is_active=True,
            preferred_schedule='evening'
        ).all()
        
        for user in users:
            try:
                tracker = ScheduleTracker.get_or_create_for_today(user.id, 'evening')
                
                if not tracker.early_sleep:
                    send_message(
                        user.telegram_id,
                        "💤 <b>تذكير النوم المبكر</b>\n\nحان وقت الخلود للنوم. النوم المبكر يساعدك على الاستيقاظ نشيطاً غداً. لا تنس تسجيل التزامك بالنوم المبكر."
                    )
            except Exception as e:
                logger.error(f"خطأ في إرسال تذكير النوم المبكر للمستخدم {user.id}: {e}")

def scheduled_check_remaining_tasks(app):
    """التحقق من المهام المتبقية وإرسال تذكير"""
    with app.app_context():
        current_time = datetime.utcnow()
        logger.info(f"تشغيل فحص المهام المتبقية في {current_time}")
        
        # الحصول على جميع المستخدمين النشطين
        users = User.query.filter_by(is_active=True).filter(
            User.preferred_schedule.in_(['morning', 'evening', 'custom'])
        ).all()
        
        for user in users:
            try:
                tracker = ScheduleTracker.get_or_create_for_today(user.id, user.preferred_schedule)
                
                # لا نرسل إشعارات للمستخدمين الذين أكملوا جدولهم
                if tracker.completed:
                    continue
                
                # الحصول على المهام المتبقية
                remaining_tasks = get_remaining_tasks(tracker, user.preferred_schedule)
                
                if remaining_tasks:
                    # جعل الرسالة تحتوي على المهمة التالية المقترحة
                    next_task = remaining_tasks[0]
                    
                    send_message(
                        user.telegram_id,
                        f"📋 <b>مهام متبقية</b>\n\nلديك {len(remaining_tasks)} مهمة متبقية لليوم.\n\nمهمتك التالية المقترحة:\n{next_task}"
                    )
            except Exception as e:
                logger.error(f"خطأ في فحص المهام المتبقية للمستخدم {user.id}: {e}")

def get_remaining_tasks(tracker, schedule_type):
    """الحصول على قائمة المهام المتبقية"""
    remaining_tasks = []
    
    # تحديد المهام حسب نوع الجدول
    if schedule_type == 'morning':
        task_map = {
            'prayer_1': 'صلاة الفجر',
            'meal_1': 'الإفطار',
            'study_1': 'المذاكرة الأولى',
            'prayer_2': 'صلاة الظهر',
            'study_2': 'المذاكرة الثانية',
            'return_after_break': 'العودة بعد الراحة',
            'prayer_3': 'صلاة العصر',
            'study_3': 'المراجعة',
            'prayer_4': 'صلاة المغرب',
            'prayer_5': 'صلاة العشاء',
            'evaluation': 'تقييم اليوم'
        }
    elif schedule_type == 'evening':
        task_map = {
            'study_1': 'المذاكرة الأولى',
            'prayer_1': 'صلاة المغرب',
            'study_2': 'المذاكرة الثانية',
            'prayer_2': 'صلاة العشاء',
            'study_3': 'الحفظ/القراءة',
            'evaluation': 'تقييم اليوم',
            'early_sleep': 'النوم المبكر'
        }
    else:
        # للجداول المخصصة، نستخدم مهام أساسية
        task_map = {
            'study_1': 'المذاكرة',
            'evaluation': 'تقييم اليوم'
        }
    
    # التحقق من كل مهمة
    for task_key, task_name in task_map.items():
        if hasattr(tracker, task_key) and not getattr(tracker, task_key):
            remaining_tasks.append(task_name)
    
    return remaining_tasks

def scheduled_update_system_stats(app):
    """تحديث إحصائيات النظام"""
    with app.app_context():
        current_time = datetime.utcnow()
        logger.info(f"تشغيل تحديث إحصائيات النظام في {current_time}")
        
        try:
            # الحصول على عدد المستخدمين النشطين
            active_users_count = User.query.filter_by(is_active=True).count()
            
            # الحصول على عدد الأنشطة المسجلة اليوم
            today = datetime.utcnow().date()
            activities_count = UserActivity.query.filter(
                UserActivity.timestamp >= datetime(today.year, today.month, today.day)
            ).count()
            
            # إنشاء أو تحديث إحصائيات اليوم
            stat = SystemStat.get_or_create_for_today()
            stat.active_users = active_users_count
            stat.activities_recorded = activities_count
            
            db.session.commit()
            logger.info(f"تم تحديث إحصائيات النظام: {active_users_count} مستخدم نشط، {activities_count} نشاط مسجل")
        except Exception as e:
            logger.error(f"خطأ في تحديث إحصائيات النظام: {e}")

def scheduled_send_motivational_messages(app):
    """إرسال رسائل تحفيزية للمستخدمين"""
    with app.app_context():
        current_time = datetime.utcnow()
        logger.info(f"تشغيل إرسال رسائل تحفيزية في {current_time}")
        
        # الحصول على المستخدمين الذين فعلوا الرسائل التحفيزية
        users = User.query.filter_by(
            is_active=True,
            motivation_enabled=True
        ).all()
        
        from study_bot.models import MotivationalMessage
        
        for user in users:
            try:
                # اختيار نوع الرسالة المناسب
                if current_time.hour < 12:
                    message = MotivationalMessage.get_random_message('morning')
                else:
                    message = MotivationalMessage.get_random_message('evening')
                
                # إرسال الرسالة التحفيزية
                motivation_text = f"""
<b>✨ رسالة تحفيزية لك:</b>

"{message}"

<b>استمر في رحلتك نحو النجاح! 🚀</b>
"""
                send_message(user.telegram_id, motivation_text)
            except Exception as e:
                logger.error(f"خطأ في إرسال رسالة تحفيزية للمستخدم {user.id}: {e}")

def scheduled_smart_notifications(app):
    """مجدول الإشعارات الذكية"""
    with app.app_context():
        current_time = datetime.utcnow()
        logger.info(f"تشغيل مجدول الإشعارات الذكية في {current_time}")
        
        # الحصول على المستخدمين الذين فعلوا محسن الإشعارات الذكي
        users = User.query.filter_by(
            is_active=True,
            smart_notifications_enabled=True
        ).all()
        
        for user in users:
            try:
                # حساب الوقت الأمثل للإشعار
                optimal_times = user.get_optimal_notification_times()
                
                if not optimal_times:
                    continue
                
                # التحقق من المهام المتبقية
                tracker = ScheduleTracker.get_or_create_for_today(user.id, user.preferred_schedule)
                
                # لا نرسل إشعارات للمستخدمين الذين أكملوا جدولهم
                if tracker.completed:
                    continue
                
                # الحصول على الإشعار الأنسب للوقت الحالي
                notification = get_best_notification_for_time(user, tracker, current_time, optimal_times)
                
                if notification:
                    send_message(user.telegram_id, notification)
            except Exception as e:
                logger.error(f"خطأ في جدولة الإشعارات الذكية للمستخدم {user.id}: {e}")

def get_best_notification_for_time(user, tracker, current_time, optimal_times):
    """تحديد أفضل إشعار للوقت الحالي"""
    # هذه الدالة ستختار الإشعار الأنسب للوقت الحالي بناءً على عدة عوامل:
    # 1. المهام التي لم يكملها المستخدم
    # 2. وقت اليوم
    # 3. تفضيلات المستخدم
    
    # تحديد الوقت الحالي بتنسيق الساعة:الدقيقة
    current_hour = current_time.hour
    
    # تقسيم اليوم إلى فترات
    if 5 <= current_hour < 12:
        period = 'morning'
    elif 12 <= current_hour < 17:
        period = 'afternoon'
    elif 17 <= current_hour < 20:
        period = 'evening'
    else:
        period = 'night'
    
    # تحديد المهام المناسبة للفترة الحالية
    if period == 'morning':
        tasks = [
            ('prayer_1', 'لا تنس صلاة الفجر 🕌'),
            ('meal_1', 'هل تناولت إفطارك اليوم؟ 🍳'),
            ('study_1', 'وقت مثالي للمذاكرة الصباحية! 📚')
        ]
    elif period == 'afternoon':
        tasks = [
            ('prayer_2', 'حان وقت صلاة الظهر 🕌'),
            ('prayer_3', 'لا تنس صلاة العصر 🕌'),
            ('study_2', 'المذاكرة بعد الظهر مفيدة للتركيز 📚'),
            ('return_after_break', 'أخذت قسطاً من الراحة؟ حان وقت العودة للمذاكرة 🔄')
        ]
    elif period == 'evening':
        tasks = [
            ('prayer_4', 'حان وقت صلاة المغرب 🕌'),
            ('study_3', 'استغل الوقت المسائي للمراجعة 📝'),
            ('prayer_5', 'لا تنس صلاة العشاء 🕌')
        ]
    else:  # night
        tasks = [
            ('evaluation', 'قبل النوم، قيّم إنجازاتك اليوم 📋'),
            ('early_sleep', 'النوم المبكر يساعد على الاستيقاظ نشيطاً غداً 💤')
        ]
    
    # فحص المهام التي لم يكملها المستخدم
    incomplete_tasks = []
    for task_key, message in tasks:
        if hasattr(tracker, task_key) and not getattr(tracker, task_key):
            incomplete_tasks.append((task_key, message))
    
    # إذا لم تكن هناك مهام غير مكتملة، نعود None
    if not incomplete_tasks:
        return None
    
    # اختيار مهمة عشوائية من المهام غير المكتملة
    import random
    task_key, message = random.choice(incomplete_tasks)
    
    # بناء الإشعار
    notification = f"""
<b>⏰ تذكير ذكي</b>

{message}

استخدم أمر /schedule لعرض جدولك وتسجيل إكمال المهام.
"""
    
    return notification
