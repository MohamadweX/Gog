#!/usr/bin/env python3
"""
مجدول مهام المجموعات والمعسكرات
يحتوي على وظائف لجدولة المهام الخاصة بالمجموعات والمعسكرات
"""

from datetime import datetime, timedelta
import random

from study_bot.config import logger, get_current_time
from study_bot.models import db, User, Group
from study_bot.group_tasks import (
    send_group_morning_message, send_group_evening_message, send_motivation_to_group,
    send_task_by_type, send_scheduled_task, check_group_schedule_tasks,
    send_morning_schedule_tasks, send_evening_schedule_tasks
)


# وظيفة لجدولة رسالة الجدول الصباحي للمجموعات
def schedule_group_morning_message():
    try:
        now = get_current_time()
        hour = now.hour
        
        # تحقق من الوقت المناسب لإرسال الجدول الصباحي (من 5 إلى 7 صباحاً)
        if 5 <= hour <= 7:
            # الحصول على مجموعات نشطة بجدول صباحي
            active_groups = Group.query.filter_by(is_active=True, morning_schedule_enabled=True).all()
            
            sent_count = 0
            for group in active_groups:
                # إرسال رسالة الجدول الصباحي
                result = send_group_morning_message(group.telegram_id)
                if result:
                    sent_count += 1
                    
            logger.info(f"تم إرسال الجدول الصباحي إلى {sent_count} مجموعة")
            return sent_count
        return 0
    except Exception as e:
        logger.error(f"خطأ في جدولة رسالة الصباح: {e}")
        return 0


# وظيفة لجدولة رسالة الجدول المسائي للمجموعات
def schedule_group_evening_message():
    try:
        now = get_current_time()
        hour = now.hour
        
        # تحقق من الوقت المناسب لإرسال الجدول المسائي (من 17 إلى 18 مساءً)
        if 17 <= hour <= 18:
            # الحصول على مجموعات نشطة بجدول مسائي
            active_groups = Group.query.filter_by(is_active=True, evening_schedule_enabled=True).all()
            
            sent_count = 0
            for group in active_groups:
                # إرسال رسالة الجدول المسائي
                result = send_group_evening_message(group.telegram_id)
                if result:
                    sent_count += 1
                    
            logger.info(f"تم إرسال الجدول المسائي إلى {sent_count} مجموعة")
            return sent_count
        return 0
    except Exception as e:
        logger.error(f"خطأ في جدولة رسالة المساء: {e}")
        return 0


# وظيفة لإرسال رسائل تحفيزية للمجموعات
def send_group_motivation_messages():
    try:
        now = get_current_time()
        
        # تسجيل الوقت للتشخيص
        logger.info(f"تشغيل مجدول إرسال رسائل تحفيزية للمجموعات في {now.strftime('%H:%M:%S')}")
        
        # الحصول على مجموعات نشطة مع تفعيل الرسائل التحفيزية
        active_groups = Group.query.filter_by(is_active=True, motivation_enabled=True).all()
        logger.info(f"تم العثور على {len(active_groups)} مجموعة نشطة مع تفعيل الرسائل التحفيزية")
        
        # اختيار المجموعات بشكل عشوائي لتجنب إرسال رسائل لجميع المجموعات في نفس الوقت
        # سنختار 25% من المجموعات لإرسال رسائل تحفيزية إليها في كل ساعة
        target_percentage = 0.25
        
        # التأكد من اختيار على الأقل مجموعة واحدة إذا كانت هناك مجموعات نشطة
        select_count = max(1, int(len(active_groups) * target_percentage)) if active_groups else 0
        selected_groups = random.sample(active_groups, select_count) if select_count > 0 else []
        
        logger.info(f"تم اختيار {len(selected_groups)} مجموعة لإرسال رسائل تحفيزية")
        
        sent_count = 0
        for group in selected_groups:
            # إرسال رسالة تحفيزية
            result = send_motivation_to_group(group.telegram_id)
            if result:
                sent_count += 1
                logger.info(f"تم إرسال رسالة تحفيزية إلى مجموعة {group.title} (ID: {group.telegram_id})")
            else:
                logger.error(f"فشل في إرسال رسالة تحفيزية إلى مجموعة {group.title} (ID: {group.telegram_id})")
                
        logger.info(f"تم إرسال رسائل تحفيزية إلى {sent_count} مجموعة")
        return sent_count
    except Exception as e:
        logger.error(f"خطأ في إرسال رسائل تحفيزية للمجموعات: {e}")
        return 0


# وظيفة لإنشاء وإرسال تقرير يومي للمجموعات
def generate_group_daily_report():
    try:
        now = get_current_time()
        hour = now.hour
        
        # إرسال التقرير اليومي في نهاية اليوم (22-23 مساءً)
        if 22 <= hour <= 23:
            # يمكن إضافة المزيد من التقارير هنا للمجموعات الأخرى
            
            logger.info("تم إرسال التقارير اليومية للمجموعات")
            return True
        return False
    except Exception as e:
        logger.error(f"خطأ في إنشاء التقرير اليومي للمجموعات: {e}")
        return False


# وظيفة لإعادة تعيين إحصائيات المجموعات اليومية
def reset_group_daily_stats():
    """إعادة تعيين إحصائيات المجموعات اليومية وفحص المهام المجدولة"""
    try:
        now = get_current_time()
        hour = now.hour
        
        # تسجيل الوقت للتشخيص
        logger.info(f"تشغيل وظيفة reset_group_daily_stats في الساعة {hour}")
        
        # إعادة تعيين الإحصائيات في منتصف الليل (0-1 صباحاً)
        if 0 <= hour <= 1:
            # هنا يمكن إضافة منطق إعادة تعيين الإحصائيات اليومية للمجموعات
            
            logger.info("تم إعادة تعيين إحصائيات المجموعات اليومية")
            return True
        
        # استدعاء وظائف فحص المهام المجدولة
        try:
            # تسجيل وقت الفحص
            time_str = now.strftime("%H:%M")
            logger.info(f"فحص مهام الجدول الصباحي للوقت {time_str}")
            
            # فحص مهام الجدول الصباحي
            morning_count = send_morning_schedule_tasks()
            logger.info(f"تم إرسال {morning_count} مهمة صباحية للوقت {time_str}")
            
            # فحص مهام الجدول المسائي
            logger.info(f"فحص مهام الجدول المسائي للوقت {time_str}")
            evening_count = send_evening_schedule_tasks()
            logger.info(f"تم إرسال {evening_count} مهمة مسائية للوقت {time_str}")
        except Exception as inner_e:
            logger.error(f"خطأ في إرسال مهام الجداول: {inner_e}")
        
        return False
    except Exception as e:
        logger.error(f"خطأ في إعادة تعيين إحصائيات المجموعات اليومية: {e}")
        return False