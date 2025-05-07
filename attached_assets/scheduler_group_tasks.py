#!/usr/bin/env python3
"""
مجدول مهام المجموعات والمعسكرات
يحتوي على وظائف لجدولة المهام الخاصة بالمجموعات والمعسكرات
"""

from datetime import datetime, timedelta
import random

from study_bot.config import logger
from study_bot.models import db, User, Group, GroupParticipant
from study_bot.group_tasks import send_group_morning_message, send_group_evening_message, send_motivation_to_group
from study_bot.custom_camps import check_scheduled_camp_tasks, send_camp_reports


# وظيفة لجدولة رسالة الجدول الصباحي للمجموعات
def schedule_group_morning_message():
    try:
        now = datetime.utcnow()
        hour = now.hour
        
        # تحقق من الوقت المناسب لإرسال الجدول الصباحي (من 5 إلى 7 صباحاً)
        if 5 <= hour <= 7:
            # الحصول على مجموعات نشطة بجدول صباحي
            active_groups = Group.query.filter_by(is_active=True, schedule_type='morning').all()
            
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
        now = datetime.utcnow()
        hour = now.hour
        
        # تحقق من الوقت المناسب لإرسال الجدول المسائي (من 17 إلى 18 مساءً)
        if 17 <= hour <= 18:
            # الحصول على مجموعات نشطة بجدول مسائي
            active_groups = Group.query.filter_by(is_active=True, schedule_type='evening').all()
            
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
        now = datetime.utcnow()
        
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
        now = datetime.utcnow()
        hour = now.hour
        
        # إرسال التقرير اليومي في نهاية اليوم (22-23 مساءً)
        if 22 <= hour <= 23:
            # تنفيذ رسالة تقرير المعسكرات لليوم
            send_camp_reports()
            
            # يمكن إضافة المزيد من التقارير هنا للمجموعات الأخرى
            
            logger.info("تم إرسال التقارير اليومية للمجموعات")
            return True
        return False
    except Exception as e:
        logger.error(f"خطأ في إنشاء التقرير اليومي للمجموعات: {e}")
        return False


# وظيفة لإعادة تعيين إحصائيات المجموعات اليومية
def reset_group_daily_stats():
    try:
        now = datetime.utcnow()
        hour = now.hour
        
        # إعادة تعيين الإحصائيات في منتصف الليل (0-1 صباحاً)
        if 0 <= hour <= 1:
            # هنا يمكن إضافة منطق إعادة تعيين الإحصائيات اليومية للمجموعات
            
            # تنفيذ فحص للمهام المجدولة للمعسكرات
            check_scheduled_camp_tasks()
            
            logger.info("تم إعادة تعيين إحصائيات المجموعات اليومية")
            return True
        
        # فحص المهام المجدولة للمعسكرات كل ساعة
        check_scheduled_camp_tasks()
        
        return False
    except Exception as e:
        logger.error(f"خطأ في إعادة تعيين إحصائيات المجموعات اليومية: {e}")
        return False
