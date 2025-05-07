#!/usr/bin/env python3
"""
معسكرات الدراسة المخصصة
يحتوي على وظائف لإدارة معسكرات الدراسة المخصصة التي ينشئها مشرفو المجموعات
"""

import json
import random
from datetime import datetime, timedelta

from study_bot.config import TELEGRAM_API_URL, logger
from study_bot.models import (User, Group, GroupParticipant, 
                            GroupScheduleTracker, GroupTaskTracker,
                            GroupTaskParticipant, db)
from study_bot.camps_models import CustomCamp, CampTask, CampParticipant, CampTaskParticipation
from study_bot.group_handlers import send_group_message, answer_callback_query, edit_group_message
from study_bot.group_tasks import MOTIVATIONAL_QUOTES


# إنشاء معسكر دراسة مخصص
def create_custom_camp(group_id, admin_id, camp_name, description, start_date, end_date, max_participants=0):
    """إنشاء معسكر دراسة مخصص جديد"""
    try:
        # التحقق من المجموعة
        group = Group.query.get(group_id)
        if not group:
            logger.error(f"لم يتم العثور على المجموعة {group_id}")
            return None
        
        # التحقق من صلاحيات المشرف
        if admin_id != group.admin_id:
            logger.error(f"المستخدم {admin_id} ليس مشرف المجموعة {group_id}")
            return None
        
        # إنشاء معسكر دراسة جديد
        camp = CustomCamp(
            group_id=group.id,
            name=camp_name,
            description=description,
            created_by=admin_id,
            start_date=start_date,
            end_date=end_date,
            max_participants=max_participants,
            is_active=True
        )
        
        db.session.add(camp)
        db.session.commit()
        
        logger.info(f"تم إنشاء معسكر دراسة جديد: {camp_name} للمجموعة {group_id}")
        
        # إرسال رسالة إعلانية للمجموعة
        send_camp_announcement(group.telegram_id, camp)
        
        return camp
    except Exception as e:
        logger.error(f"خطأ في إنشاء معسكر دراسة مخصص: {e}")
        db.session.rollback()
        return None


# إضافة مهمة لمعسكر دراسة
def add_camp_task(camp_id, admin_id, task_title, task_description, scheduled_time, points=1, deadline_minutes=10):
    """إضافة مهمة إلى معسكر دراسة"""
    try:
        # التحقق من المعسكر
        camp = CustomCamp.query.get(camp_id)
        if not camp:
            logger.error(f"لم يتم العثور على المعسكر {camp_id}")
            return None
        
        # التحقق من المشرف
        if admin_id != camp.created_by:
            logger.error(f"المستخدم {admin_id} ليس مشرف المعسكر {camp_id}")
            return None
        
        # إنشاء مهمة جديدة
        task = CampTask(
            camp_id=camp.id,
            title=task_title,
            description=task_description,
            scheduled_time=scheduled_time,
            points=points,
            deadline_minutes=deadline_minutes,
            is_sent=False
        )
        
        db.session.add(task)
        db.session.commit()
        
        logger.info(f"تم إضافة مهمة جديدة: {task_title} للمعسكر {camp.name}")
        return task
    except Exception as e:
        logger.error(f"خطأ في إضافة مهمة لمعسكر دراسة: {e}")
        db.session.rollback()
        return None


# الانضمام لمعسكر دراسة
def join_camp(camp_id, user_id):
    """الانضمام لمعسكر دراسة"""
    try:
        # التحقق من المعسكر
        camp = CustomCamp.query.get(camp_id)
        if not camp or not camp.is_active:
            logger.error(f"لم يتم العثور على المعسكر النشط {camp_id}")
            return None
        
        # التحقق من سعة المعسكر
        if camp.max_participants > 0:
            current_participants = CampParticipant.query.filter_by(camp_id=camp.id, is_active=True).count()
            if current_participants >= camp.max_participants:
                logger.warning(f"المعسكر {camp.name} ممتلئ ({current_participants}/{camp.max_participants})")
                return None
        
        # التحقق من عدم الانضمام سابقاً
        existing_participant = CampParticipant.query.filter_by(camp_id=camp.id, user_id=user_id, is_active=True).first()
        if existing_participant:
            logger.info(f"المستخدم {user_id} منضم بالفعل للمعسكر {camp.name}")
            return existing_participant
        
        # إنشاء مشارك جديد
        user = User.get_or_create(user_id)
        participant = CampParticipant(
            camp_id=camp.id,
            user_id=user.id,
            join_date=datetime.utcnow(),
            is_active=True,
            total_points=0
        )
        
        db.session.add(participant)
        db.session.commit()
        
        logger.info(f"تم انضمام المستخدم {user_id} للمعسكر {camp.name}")
        return participant
    except Exception as e:
        logger.error(f"خطأ في الانضمام لمعسكر دراسة: {e}")
        db.session.rollback()
        return None


# إرسال إعلان عن معسكر جديد
def send_camp_announcement(group_telegram_id, camp):
    """إرسال إعلان عن معسكر جديد"""
    try:
        # إعداد نص الإعلان
        start_date_str = camp.start_date.strftime('%Y-%m-%d')
        end_date_str = camp.end_date.strftime('%Y-%m-%d')
        
        text = f"""
🎓 <b>معسكر دراسة جديد!</b>

<b>{camp.name}</b>

{camp.description}

📅 الفترة: من {start_date_str} إلى {end_date_str}
"""
        
        if camp.max_participants > 0:
            text += f"👥 الحد الأقصى للمشاركين: {camp.max_participants} مشارك"
        
        # إضافة اقتباس تحفيزي
        motivation = random.choice(MOTIVATIONAL_QUOTES)
        text += f"\n\n✨ {motivation}"
        
        # إنشاء زر الانضمام
        keyboard = {
            "inline_keyboard": [
                [{
                    "text": "💪 انضم للمعسكر",
                    "callback_data": f"camp_join:{camp.id}"
                }]
            ]
        }
        
        # إرسال الإعلان
        message = send_group_message(group_telegram_id, text, keyboard)
        if message:
            # تحديث message_id في قاعدة البيانات
            camp.announcement_message_id = message.get('message_id')
            db.session.commit()
            logger.info(f"تم إرسال إعلان المعسكر {camp.name} إلى المجموعة {group_telegram_id}")
            return message
    except Exception as e:
        logger.error(f"خطأ في إرسال إعلان معسكر: {e}")
        return None


# إرسال مهمة معسكر
def send_camp_task(task_id):
    """إرسال مهمة من مهام المعسكر"""
    try:
        # الحصول على المهمة
        task = CampTask.query.get(task_id)
        if not task:
            logger.error(f"لم يتم العثور على المهمة {task_id}")
            return None
        
        # التحقق من أن المهمة لم ترسل بعد
        if task.is_sent:
            logger.warning(f"المهمة {task.title} مرسلة بالفعل")
            return None
            
        # الحصول على المعسكر والمجموعة
        camp = CustomCamp.query.get(task.camp_id)
        if not camp or not camp.is_active:
            logger.error(f"المعسكر غير موجود أو غير نشط للمهمة {task_id}")
            return None
            
        group = Group.query.get(camp.group_id)
        if not group:
            logger.error(f"لم يتم العثور على المجموعة للمعسكر {camp.id}")
            return None
        
        # إعداد نص المهمة
        text = f"""
📝 <b>{task.title}</b> - <i>معسكر {camp.name}</i>

{task.description}
"""
        
        # إضافة معلومات المهلة والنقاط
        deadline_text = f"⏰ يمكنك الانضمام خلال {task.deadline_minutes} دقائق فقط"
        points_text = f"🏆 ستحصل على {task.points} نقاط عند المشاركة"
        
        # إضافة اقتباس تحفيزي
        motivation = random.choice(MOTIVATIONAL_QUOTES)
        
        # إنشاء نص الرسالة الكامل
        full_text = f"{text}\n\n✨ {motivation}\n\n{deadline_text}\n{points_text}"
        
        # إنشاء زر المشاركة
        keyboard = {
            "inline_keyboard": [
                [{
                    "text": "✅ شارك في المهمة",
                    "callback_data": f"camp_task_join:{task.id}"
                }]
            ]
        }
        
        # إرسال الرسالة
        message = send_group_message(group.telegram_id, full_text, keyboard)
        if message:
            # تحديث حالة المهمة
            task.is_sent = True
            task.message_id = message.get('message_id')
            task.sent_at = datetime.utcnow()
            db.session.commit()
            
            logger.info(f"تم إرسال مهمة المعسكر {task.title} إلى المجموعة {group.telegram_id}")
            return message
    except Exception as e:
        logger.error(f"خطأ في إرسال مهمة معسكر: {e}")
        return None


# معالجة طلب الانضمام لمعسكر
def handle_camp_join(camp_id, user_id, callback_query_id):
    """معالجة طلب الانضمام لمعسكر"""
    try:
        # التحقق من المعسكر
        camp = CustomCamp.query.get(camp_id)
        if not camp or not camp.is_active:
            answer_callback_query(callback_query_id, "❌ لم يتم العثور على المعسكر أو أنه غير نشط")
            return False
        
        # التحقق من موعد المعسكر
        today = datetime.utcnow().date()
        if today < camp.start_date.date() or today > camp.end_date.date():
            answer_callback_query(callback_query_id, "❌ المعسكر ليس في الفترة النشطة")
            return False
        
        # التحقق من سعة المعسكر
        if camp.max_participants > 0:
            current_participants = CampParticipant.query.filter_by(camp_id=camp.id, is_active=True).count()
            if current_participants >= camp.max_participants:
                answer_callback_query(callback_query_id, f"❌ المعسكر ممتلئ ({current_participants}/{camp.max_participants})")
                return False
        
        # التحقق من عدم الانضمام سابقاً
        existing_participant = CampParticipant.query.filter_by(camp_id=camp.id, user_id=user_id, is_active=True).first()
        if existing_participant:
            answer_callback_query(callback_query_id, "✅ أنت منضم بالفعل لهذا المعسكر!")
            return True
        
        # إنشاء مشارك جديد
        participant = join_camp(camp.id, user_id)
        if participant:
            answer_callback_query(callback_query_id, f"✅ تم انضمامك لمعسكر {camp.name} بنجاح!")
            
            # تحديث عدد المشاركين في الإعلان
            if camp.announcement_message_id:
                update_camp_announcement(camp.id)
                
            return True
        else:
            answer_callback_query(callback_query_id, "❌ حدث خطأ أثناء الانضمام للمعسكر")
            return False
    except Exception as e:
        logger.error(f"خطأ في معالجة طلب الانضمام لمعسكر: {e}")
        answer_callback_query(callback_query_id, "❌ حدث خطأ أثناء معالجة طلبك")
        return False


# معالجة طلب المشاركة في مهمة معسكر
def handle_camp_task_join(task_id, user_id, callback_query_id):
    """معالجة طلب المشاركة في مهمة معسكر"""
    try:
        # الحصول على المهمة
        task = CampTask.query.get(task_id)
        if not task or not task.is_sent:
            answer_callback_query(callback_query_id, "❌ لم يتم العثور على المهمة المطلوبة")
            return False
        
        # التحقق من المهلة الزمنية
        if task.sent_at:
            deadline = task.sent_at + timedelta(minutes=task.deadline_minutes)
            if datetime.utcnow() > deadline:
                answer_callback_query(callback_query_id, "❌ انتهت مهلة المشاركة في هذه المهمة")
                return False
        
        # الحصول على المعسكر
        camp = CustomCamp.query.get(task.camp_id)
        if not camp or not camp.is_active:
            answer_callback_query(callback_query_id, "❌ المعسكر غير نشط")
            return False
        
        # التحقق من أن المستخدم منضم للمعسكر
        participant = CampParticipant.query.filter_by(camp_id=camp.id, user_id=user_id, is_active=True).first()
        if not participant:
            answer_callback_query(callback_query_id, "❌ يجب أن تنضم للمعسكر أولاً")
            return False
        
        # التحقق من عدم المشاركة سابقاً
        user = User.get_or_create(user_id)
        existing_participation = db.session.query(CampTaskParticipation).filter_by(
            task_id=task.id, 
            participant_id=participant.id
        ).first()
        
        if existing_participation:
            answer_callback_query(callback_query_id, "✅ لقد شاركت بالفعل في هذه المهمة!")
            return True
        
        # إنشاء مشاركة جديدة
        participation = CampTaskParticipation(
            task_id=task.id,
            participant_id=participant.id,
            participation_time=datetime.utcnow(),
            points_earned=task.points
        )
        
        db.session.add(participation)
        
        # تحديث نقاط المشارك
        participant.total_points += task.points
        db.session.commit()
        
        # إرسال تأكيد للمستخدم
        answer_callback_query(
            callback_query_id, 
            f"✅ تم تسجيل مشاركتك في مهمة '{task.title}'! (+{task.points} نقطة)"
        )
        
        logger.info(f"تم تسجيل مشاركة المستخدم {user_id} في مهمة المعسكر {task.title}")
        return True
    except Exception as e:
        logger.error(f"خطأ في معالجة طلب المشاركة في مهمة معسكر: {e}")
        answer_callback_query(callback_query_id, "❌ حدث خطأ أثناء معالجة طلبك")
        return False


# تحديث إعلان المعسكر
def update_camp_announcement(camp_id):
    """تحديث إعلان المعسكر بمعلومات جديدة"""
    try:
        # الحصول على المعسكر
        camp = CustomCamp.query.get(camp_id)
        if not camp or not camp.announcement_message_id:
            logger.error(f"لم يتم العثور على المعسكر أو رسالة الإعلان {camp_id}")
            return None
            
        # الحصول على المجموعة
        group = Group.query.get(camp.group_id)
        if not group:
            logger.error(f"لم يتم العثور على المجموعة للمعسكر {camp.id}")
            return None
        
        # حساب عدد المشاركين
        participants_count = CampParticipant.query.filter_by(camp_id=camp.id, is_active=True).count()
        
        # إعداد نص الإعلان المحدث
        start_date_str = camp.start_date.strftime('%Y-%m-%d')
        end_date_str = camp.end_date.strftime('%Y-%m-%d')
        
        text = f"""
🎓 <b>معسكر دراسة!</b>

<b>{camp.name}</b>

{camp.description}

📅 الفترة: من {start_date_str} إلى {end_date_str}
👥 المشاركون حالياً: {participants_count}"""
        
        if camp.max_participants > 0:
            text += f" / {camp.max_participants}"
            
            # التحقق إذا كان المعسكر ممتلئًا
            if participants_count >= camp.max_participants:
                text += "\n\n⛔ <b>المعسكر ممتلئ حالياً</b>"
        
        # إضافة اقتباس تحفيزي
        motivation = random.choice(MOTIVATIONAL_QUOTES)
        text += f"\n\n✨ {motivation}"
        
        # إنشاء زر الانضمام
        keyboard = {
            "inline_keyboard": [
                [{
                    "text": "💪 انضم للمعسكر",
                    "callback_data": f"camp_join:{camp.id}"
                }]
            ]
        }
        
        # في حالة امتلاء المعسكر، تغيير النص وتعطيل الزر
        if camp.max_participants > 0 and participants_count >= camp.max_participants:
            keyboard = {
                "inline_keyboard": [
                    [{
                        "text": "⛔ المعسكر ممتلئ",
                        "callback_data": "camp_full"
                    }]
                ]
            }
        
        # تحديث الرسالة
        result = edit_group_message(group.telegram_id, camp.announcement_message_id, text, keyboard)
        if result:
            logger.info(f"تم تحديث إعلان المعسكر {camp.name}")
            return result
    except Exception as e:
        logger.error(f"خطأ في تحديث إعلان معسكر: {e}")
        return None


# رفع تقرير عن المعسكر
def send_camp_report(camp_id):
    """إرسال تقرير عن أداء المعسكر"""
    try:
        # الحصول على المعسكر
        camp = CustomCamp.query.get(camp_id)
        if not camp:
            logger.error(f"لم يتم العثور على المعسكر {camp_id}")
            return None
            
        # الحصول على المجموعة
        group = Group.query.get(camp.group_id)
        if not group:
            logger.error(f"لم يتم العثور على المجموعة للمعسكر {camp.id}")
            return None
        
        # جمع إحصائيات المعسكر
        participants = CampParticipant.query.filter_by(camp_id=camp.id, is_active=True).all()
        participants_count = len(participants)
        
        if participants_count == 0:
            return send_group_message(
                group.telegram_id, 
                f"📊 <b>تقرير معسكر {camp.name}</b>\n\nلم ينضم أي مشارك لهذا المعسكر بعد."
            )
        
        # إعداد قائمة المتصدرين
        participants.sort(key=lambda p: p.total_points, reverse=True)
        top_participants = participants[:10]  # أفضل 10 مشاركين
        
        # جمع معلومات المهام
        tasks = CampTask.query.filter_by(camp_id=camp.id, is_sent=True).all()
        tasks_count = len(tasks)
        
        # إعداد نص التقرير
        report_text = f"""
📊 <b>تقرير معسكر {camp.name}</b>

👥 عدد المشاركين: {participants_count}
📝 عدد المهام المرسلة: {tasks_count}

<b>🏆 قائمة المتصدرين:</b>
"""
        
        # إضافة قائمة المتصدرين
        for i, participant in enumerate(top_participants):
            user = User.query.get(participant.user_id)
            if user:
                username = user.username if user.username else f"{user.first_name or ''} {user.last_name or ''}".strip()
                report_text += f"{i+1}. {username}: {participant.total_points} نقطة\n"
        
        # إرسال التقرير
        return send_group_message(group.telegram_id, report_text)
    except Exception as e:
        logger.error(f"خطأ في إرسال تقرير معسكر: {e}")
        return None


# معالجة أمر إنشاء معسكر جديد
def handle_create_camp_command(group_id, admin_id, command_text):
    """معالجة أمر إنشاء معسكر جديد"""
    try:
        # التحقق من المجموعة
        group = Group.query.get(group_id)
        if not group:
            return "❌ لم يتم العثور على المجموعة"
            
        # التحقق من صلاحيات المشرف
        if admin_id != group.admin_id:
            return "❌ هذا الأمر متاح فقط لمشرف المجموعة"
        
        # تحليل نص الأمر
        params = command_text.strip().split('|')
        if len(params) < 4:
            return "❌ صيغة غير صحيحة. الرجاء استخدام:\n/create_camp <اسم المعسكر> | <وصف المعسكر> | <تاريخ البداية YYYY-MM-DD> | <تاريخ النهاية YYYY-MM-DD> | [الحد الأقصى للمشاركين]"
        
        # الحصول على المعلومات
        camp_name = params[0].strip()
        description = params[1].strip()
        
        # تحليل التواريخ
        try:
            start_date = datetime.strptime(params[2].strip(), '%Y-%m-%d')
            end_date = datetime.strptime(params[3].strip(), '%Y-%m-%d')
            
            # التحقق من التواريخ
            if start_date > end_date:
                return "❌ تاريخ البداية يجب أن يكون قبل تاريخ النهاية"
        except ValueError:
            return "❌ صيغة التاريخ غير صحيحة. يرجى استخدام الصيغة: YYYY-MM-DD"
        
        # الحد الأقصى للمشاركين (اختياري)
        max_participants = 0
        if len(params) > 4:
            try:
                max_participants = int(params[4].strip())
                if max_participants < 0:
                    return "❌ يجب أن يكون الحد الأقصى للمشاركين عدداً موجباً"
            except ValueError:
                return "❌ يجب أن يكون الحد الأقصى للمشاركين عدداً صحيحاً"
        
        # إنشاء المعسكر
        camp = create_custom_camp(
            group_id=group.id, 
            admin_id=admin_id, 
            camp_name=camp_name, 
            description=description,
            start_date=start_date,
            end_date=end_date,
            max_participants=max_participants
        )
        
        if camp:
            max_txt = f" (الحد الأقصى: {max_participants} مشارك)" if max_participants > 0 else ""
            return f"✅ تم إنشاء معسكر '{camp_name}' بنجاح!{max_txt}\nالفترة: من {params[2]} إلى {params[3]}"
        else:
            return "❌ حدث خطأ في إنشاء المعسكر"
    except Exception as e:
        logger.error(f"خطأ في معالجة أمر إنشاء معسكر: {e}")
        return "❌ حدث خطأ في معالجة الأمر"


# معالجة أمر إضافة مهمة لمعسكر
def handle_add_camp_task_command(group_id, admin_id, command_text):
    """معالجة أمر إضافة مهمة لمعسكر"""
    try:
        # التحقق من المجموعة
        group = Group.query.get(group_id)
        if not group:
            return "❌ لم يتم العثور على المجموعة"
            
        # التحقق من صلاحيات المشرف
        if admin_id != group.admin_id:
            return "❌ هذا الأمر متاح فقط لمشرف المجموعة"
        
        # تحليل نص الأمر
        params = command_text.strip().split('|')
        if len(params) < 5:
            return "❌ صيغة غير صحيحة. الرجاء استخدام:\n/add_camp_task <رقم المعسكر> | <عنوان المهمة> | <وصف المهمة> | <وقت الجدولة YYYY-MM-DD HH:MM> | <النقاط> | [المهلة بالدقائق]"
        
        # الحصول على المعلومات
        try:
            camp_id = int(params[0].strip())
        except ValueError:
            return "❌ رقم المعسكر يجب أن يكون عدداً صحيحاً"
        
        # التحقق من وجود المعسكر وأنه ينتمي للمجموعة
        camp = CustomCamp.query.get(camp_id)
        if not camp or camp.group_id != group.id:
            return "❌ لم يتم العثور على المعسكر المطلوب في هذه المجموعة"
        
        # التحقق من صلاحيات المشرف للمعسكر
        if admin_id != camp.created_by:
            return "❌ يمكن فقط لمنشئ المعسكر إضافة مهام"
        
        # الحصول على بيانات المهمة
        task_title = params[1].strip()
        task_description = params[2].strip()
        
        # تحليل وقت الجدولة
        try:
            scheduled_time = datetime.strptime(params[3].strip(), '%Y-%m-%d %H:%M')
            
            # التحقق من الوقت ضمن فترة المعسكر
            if scheduled_time.date() < camp.start_date.date() or scheduled_time.date() > camp.end_date.date():
                return "❌ وقت جدولة المهمة خارج فترة المعسكر"
        except ValueError:
            return "❌ صيغة الوقت غير صحيحة. يرجى استخدام الصيغة: YYYY-MM-DD HH:MM"
        
        # الحصول على النقاط والمهلة
        try:
            points = int(params[4].strip())
            if points <= 0:
                return "❌ يجب أن تكون النقاط عدداً موجباً"
                
            deadline_minutes = 10  # القيمة الافتراضية
            if len(params) > 5:
                deadline_minutes = int(params[5].strip())
                if deadline_minutes <= 0:
                    return "❌ يجب أن تكون المهلة عدداً موجباً من الدقائق"
        except ValueError:
            return "❌ يجب أن تكون النقاط والمهلة أعداداً صحيحة"
        
        # إضافة المهمة
        task = add_camp_task(
            camp_id=camp.id,
            admin_id=admin_id,
            task_title=task_title,
            task_description=task_description,
            scheduled_time=scheduled_time,
            points=points,
            deadline_minutes=deadline_minutes
        )
        
        if task:
            scheduled_time_str = scheduled_time.strftime('%Y-%m-%d %H:%M')
            return f"✅ تمت إضافة مهمة '{task_title}' لمعسكر '{camp.name}'!\nسيتم إرسالها في: {scheduled_time_str}\nالنقاط: {points}, المهلة: {deadline_minutes} دقيقة"
        else:
            return "❌ حدث خطأ في إضافة المهمة"
    except Exception as e:
        logger.error(f"خطأ في معالجة أمر إضافة مهمة لمعسكر: {e}")
        return "❌ حدث خطأ في معالجة الأمر"


# فحص مهام المعسكرات المجدولة
def check_scheduled_camp_tasks():
    """فحص وإرسال مهام المعسكرات المجدولة"""
    try:
        # الحصول على الوقت الحالي
        now = datetime.utcnow()
        # تقليل نافذة الوقت لتحسين دقة التوقيت
        two_minutes_ago = now - timedelta(minutes=2)
        two_minutes_later = now + timedelta(minutes=2)
        
        # تسجيل الوقت الحالي للتشخيص
        logger.info(f"فحص مهام المعسكرات المجدولة للفترة من {two_minutes_ago.strftime('%H:%M:%S')} إلى {two_minutes_later.strftime('%H:%M:%S')}")
        
        # البحث عن المهام المجدولة للإرسال في الوقت الحالي
        tasks = CampTask.query.filter(
            CampTask.is_sent == False,
            CampTask.scheduled_time >= two_minutes_ago,
            CampTask.scheduled_time <= two_minutes_later
        ).all()
        
        # للتشخيص: عرض المهام التي تم إيجادها
        if tasks:
            logger.info(f"تم العثور على {len(tasks)} مهمة مجدولة")
            for i, task in enumerate(tasks):
                logger.info(f"  {i+1}. '{task.title}' مجدولة للساعة {task.scheduled_time.strftime('%H:%M:%S')}")
        else:
            logger.info("لم يتم العثور على مهام مجدولة في هذه الفترة")
        
        # التحقق من أن المعسكر لا يزال نشطاً
        active_tasks = []
        for task in tasks:
            camp = CustomCamp.query.get(task.camp_id)
            if camp and camp.is_active:
                today = now.date()
                if today >= camp.start_date.date() and today <= camp.end_date.date():
                    active_tasks.append(task)
        
        # إرسال المهام النشطة
        sent_count = 0
        for task in active_tasks:
            result = send_camp_task(task.id)
            if result:
                sent_count += 1
                logger.info(f"تم إرسال مهمة '{task.title}' بنجاح")
            else:
                logger.error(f"فشل في إرسال مهمة '{task.title}'")
                
        logger.info(f"تم إرسال {sent_count} من مهام المعسكرات المجدولة")
        return sent_count
    except Exception as e:
        logger.error(f"خطأ في فحص مهام المعسكرات المجدولة: {e}")
        return 0


# إرسال تقارير المعسكرات
def send_camp_reports():
    """إرسال تقارير يومية للمعسكرات النشطة"""
    try:
        # الحصول على التاريخ الحالي
        today = datetime.utcnow().date()
        
        # البحث عن المعسكرات النشطة
        camps = CustomCamp.query.filter(
            CustomCamp.is_active == True,
            CustomCamp.start_date <= today,
            CustomCamp.end_date >= today
        ).all()
        
        # إرسال تقرير لكل معسكر
        sent_count = 0
        for camp in camps:
            result = send_camp_report(camp.id)
            if result:
                sent_count += 1
                
        logger.info(f"تم إرسال {sent_count} من تقارير المعسكرات")
        return sent_count
    except Exception as e:
        logger.error(f"خطأ في إرسال تقارير المعسكرات: {e}")
        return 0


# معالجة أمر طلب تقرير المعسكر
def handle_camp_report_command(group_id, admin_id, command_text):
    """معالجة أمر طلب تقرير المعسكر"""
    try:
        # التحقق من المجموعة
        group = Group.query.get(group_id)
        if not group:
            return "❌ لم يتم العثور على المجموعة"
            
        # التحقق من صلاحيات المشرف
        if admin_id != group.admin_id:
            return "❌ هذا الأمر متاح فقط لمشرف المجموعة"
        
        # تحليل رقم المعسكر
        try:
            camp_id = int(command_text.strip())
        except ValueError:
            # جلب جميع معسكرات المجموعة
            camps = CustomCamp.query.filter_by(group_id=group.id).all()
            if not camps:
                return "❌ لا يوجد معسكرات لهذه المجموعة"
            
            camp_list = "\n".join([f"{camp.id}. {camp.name} (من {camp.start_date.strftime('%Y-%m-%d')} إلى {camp.end_date.strftime('%Y-%m-%d')})" for camp in camps])
            return f"ℹ️ معسكرات المجموعة:\n{camp_list}\n\nلطلب تقرير عن معسكر محدد، أرسل: /camp_report <رقم المعسكر>"
        
        # التحقق من وجود المعسكر وأنه ينتمي للمجموعة
        camp = CustomCamp.query.get(camp_id)
        if not camp or camp.group_id != group.id:
            return "❌ لم يتم العثور على المعسكر المطلوب في هذه المجموعة"
        
        # إرسال تقرير المعسكر
        result = send_camp_report(camp.id)
        if result:
            return f"✅ تم إرسال تقرير معسكر '{camp.name}' بنجاح!"
        else:
            return "❌ حدث خطأ في إرسال تقرير المعسكر"
    except Exception as e:
        logger.error(f"خطأ في معالجة أمر طلب تقرير المعسكر: {e}")
        return "❌ حدث خطأ في معالجة الأمر"