#!/usr/bin/env python3
"""
مجدول مهام المعسكرات الدراسية
ملف منفصل لجدولة وإرسال مهام المعسكرات بدقة عالية
"""

import random
from datetime import datetime, timedelta
from flask import current_app

from study_bot.config import logger
from study_bot.models import db, User, Group
from study_bot.camps_models import CustomCamp, CampTask, CampParticipant, CampTaskParticipation
from study_bot.custom_camps import send_camp_task, update_camp_announcement
from study_bot.group_handlers import send_group_message


def check_and_send_scheduled_camp_tasks():
    """التحقق من مهام المعسكرات المجدولة وإرسالها"""
    try:
        # التحقق من وجود مهام يجب إرسالها
        now = datetime.utcnow()
        logger.info(f"جاري التحقق من مهام المعسكرات المجدولة في {now}")
        
        # الحصول على المهام التي يجب إرسالها (مستقبلية بدقيقة واحدة أو في الماضي ولم ترسل)
        tasks_to_send = CampTask.query.filter(
            CampTask.is_sent == False,
            CampTask.scheduled_time <= now + timedelta(minutes=1),
            CampTask.scheduled_time >= now - timedelta(minutes=15)  # إرسال المهام المتأخرة خلال 15 دقيقة ماضية
        ).all()
        
        sent_count = 0
        for task in tasks_to_send:
            # التحقق من المعسكر
            camp = CustomCamp.query.get(task.camp_id)
            if not camp or not camp.is_active:
                logger.warning(f"المعسكر {task.camp_id} غير نشط أو غير موجود للمهمة {task.id}")
                continue
                
            # التحقق من أن تاريخ المهمة يقع ضمن فترة المعسكر
            if task.scheduled_time < camp.start_date or task.scheduled_time > camp.end_date:
                logger.warning(f"المهمة {task.id} خارج فترة المعسكر {camp.id}")
                continue
            
            # إرسال المهمة
            result = send_camp_task(task.id)
            if result:
                sent_count += 1
                logger.info(f"تم إرسال مهمة المعسكر {task.id} بنجاح")
            else:
                logger.error(f"فشل إرسال مهمة المعسكر {task.id}")
            
        # تحديث إعلانات المعسكرات النشطة
        active_camps = CustomCamp.query.filter_by(is_active=True).all()
        for camp in active_camps:
            update_camp_announcement(camp.id)
            
        return sent_count
    except Exception as e:
        logger.exception(f"خطأ في التحقق من مهام المعسكرات المجدولة: {e}")
        return 0


def generate_camp_daily_report():
    """إنشاء تقرير يومي للمعسكرات"""
    try:
        now = datetime.utcnow()
        hour = now.hour
        
        # إرسال التقرير اليومي في نهاية اليوم (11 مساءً)
        if 23 <= hour <= 23:
            # الحصول على المعسكرات النشطة
            active_camps = CustomCamp.query.filter_by(is_active=True).all()
            
            for camp in active_camps:
                send_camp_daily_report(camp.id)
        
    except Exception as e:
        logger.exception(f"خطأ في إنشاء تقرير يومي للمعسكرات: {e}")
        return 0


def send_camp_daily_report(camp_id):
    """إرسال تقرير يومي لمعسكر محدد"""
    try:
        # الحصول على المعسكر
        camp = CustomCamp.query.get(camp_id)
        if not camp or not camp.is_active:
            logger.warning(f"المعسكر {camp_id} غير نشط أو غير موجود للتقرير اليومي")
            return False
            
        # الحصول على المجموعة
        group = Group.query.get(camp.group_id)
        if not group:
            logger.error(f"لم يتم العثور على المجموعة للمعسكر {camp_id}")
            return False
        
        # الحصول على مشاركي المعسكر مرتبين حسب النقاط
        top_participants = CampParticipant.query.filter_by(
            camp_id=camp.id, 
            is_active=True
        ).order_by(CampParticipant.total_points.desc()).limit(10).all()
        
        # إعداد نص التقرير
        today = datetime.utcnow().strftime('%Y-%m-%d')
        report_text = f"""
📈 <b>تقرير معسكر {camp.name} ليوم {today}</b>

🏆 <b>أفضل المشاركين:</b>
"""
        
        # إضافة قائمة المشاركين الأفضل
        if top_participants:
            for i, participant in enumerate(top_participants, 1):
                user = User.query.get(participant.user_id)
                if user:
                    name = user.first_name or f"User {user.telegram_id}"
                    report_text += f"{i}. {name}: {participant.total_points} نقطة\n"
        else:
            report_text += "لم ينضم أي مشارك بعد.\n"
        
        # إضافة معلومات إضافية
        tasks_today = CampTask.query.filter(
            CampTask.camp_id == camp.id,
            CampTask.is_sent == True,
            CampTask.sent_at >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        ).count()
        
        report_text += f"\n🗓 <b>إحصائيات اليوم:</b>\n"
        report_text += f"- عدد المهام اليوم: {tasks_today}\n"
        
        total_participants = CampParticipant.query.filter_by(camp_id=camp.id, is_active=True).count()
        report_text += f"- عدد المشاركين: {total_participants}\n"
        
        # إضافة رسالة تحفيزية
        from study_bot.group_tasks import MOTIVATIONAL_QUOTES
        motivation = random.choice(MOTIVATIONAL_QUOTES)
        report_text += f"\n✨ {motivation}\n\n"
        
        # إضافة معلومات عن مهام الغد
        tomorrow = datetime.utcnow() + timedelta(days=1)
        tomorrow_start = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow_end = tomorrow.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        tomorrow_tasks = CampTask.query.filter(
            CampTask.camp_id == camp.id,
            CampTask.scheduled_time >= tomorrow_start,
            CampTask.scheduled_time <= tomorrow_end
        ).all()
        
        if tomorrow_tasks:
            report_text += f"<b>📅 مهام الغد:</b>\n"
            for task in tomorrow_tasks:
                time_str = task.scheduled_time.strftime('%H:%M')
                report_text += f"- {time_str}: {task.title}\n"
        
        # إرسال التقرير
        result = send_group_message(group.telegram_id, report_text)
        if result:
            logger.info(f"تم إرسال التقرير اليومي للمعسكر {camp.name} بنجاح")
            return True
        else:
            logger.error(f"فشل إرسال التقرير اليومي للمعسكر {camp.name}")
            return False
            
    except Exception as e:
        logger.exception(f"خطأ في إرسال تقرير يومي للمعسكر {camp_id}: {e}")
        return False
