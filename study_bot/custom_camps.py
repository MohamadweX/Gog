"""
معسكرات الدراسة المخصصة
يحتوي على وظائف لإدارة معسكرات الدراسة المخصصة التي ينشئها مشرفو المجموعات
"""

import re
import random
import traceback
from datetime import datetime, timedelta

from study_bot.config import logger
from study_bot.models import db


def create_custom_camp(group_id, admin_id, camp_name, description, start_date, end_date, max_participants=0):
    """إنشاء معسكر دراسة مخصص جديد"""
    try:
        from study_bot.models import Group, CustomCamp
        
        # التحقق من المجموعة
        group = Group.query.get(group_id)
        if not group or not group.is_active:
            logger.error(f"المجموعة {group_id} غير موجودة أو غير نشطة")
            return None
        
        # التحقق من صحة التواريخ
        if start_date >= end_date:
            logger.error(f"تاريخ البدء {start_date} يجب أن يكون قبل تاريخ الانتهاء {end_date}")
            return None
        
        # التحقق من أن تاريخ البدء في المستقبل
        now = datetime.utcnow()
        if start_date <= now:
            logger.error(f"تاريخ البدء {start_date} يجب أن يكون في المستقبل")
            return None
        
        # إنشاء المعسكر الجديد
        new_camp = CustomCamp(
            group_id=group.id,
            name=camp_name,
            description=description,
            created_by=admin_id,
            start_date=start_date,
            end_date=end_date,
            max_participants=max_participants,
            is_active=True
        )
        
        db.session.add(new_camp)
        db.session.commit()
        
        logger.info(f"تم إنشاء معسكر جديد بمعرف {new_camp.id} للمجموعة {group_id}")
        
        # إرسال إعلان عن المعسكر الجديد
        send_camp_announcement(group.telegram_id, new_camp)
        
        return new_camp
    except Exception as e:
        logger.error(f"خطأ في إنشاء معسكر دراسة مخصص: {e}")
        logger.error(traceback.format_exc())
        return None


def add_camp_task(camp_id, admin_id, task_title, task_description, scheduled_time, points=1, deadline_minutes=10):
    """إضافة مهمة إلى معسكر دراسة"""
    try:
        from study_bot.models import CustomCamp, CampTask
        
        # التحقق من المعسكر
        camp = CustomCamp.query.get(camp_id)
        if not camp or not camp.is_active:
            logger.error(f"المعسكر {camp_id} غير موجود أو غير نشط")
            return None
        
        # التحقق من أن المشرف هو من أنشأ المعسكر أو مشرف المجموعة
        from study_bot.models import Group
        group = Group.query.get(camp.group_id)
        
        if camp.created_by != admin_id and group.admin_id != admin_id:
            logger.error(f"المستخدم {admin_id} ليس مشرفًا على المعسكر {camp_id}")
            return None
        
        # التحقق من صحة الوقت
        if not isinstance(scheduled_time, datetime):
            logger.error(f"الوقت {scheduled_time} ليس من نوع datetime")
            return None
        
        # التحقق من أن الوقت في نطاق المعسكر
        if scheduled_time < camp.start_date or scheduled_time > camp.end_date:
            logger.error(f"الوقت {scheduled_time} خارج نطاق المعسكر ({camp.start_date} - {camp.end_date})")
            return None
        
        # التحقق من أن الوقت في المستقبل
        now = datetime.utcnow()
        if scheduled_time <= now:
            logger.error(f"الوقت {scheduled_time} يجب أن يكون في المستقبل")
            return None
        
        # إنشاء المهمة الجديدة
        new_task = CampTask(
            camp_id=camp.id,
            title=task_title,
            description=task_description,
            scheduled_time=scheduled_time,
            points=points,
            deadline_minutes=deadline_minutes,
            is_sent=False
        )
        
        db.session.add(new_task)
        db.session.commit()
        
        logger.info(f"تم إضافة مهمة جديدة بمعرف {new_task.id} للمعسكر {camp_id}")
        
        # تحديث إعلان المعسكر
        update_camp_announcement(camp.id)
        
        return new_task
    except Exception as e:
        logger.error(f"خطأ في إضافة مهمة إلى معسكر دراسة: {e}")
        logger.error(traceback.format_exc())
        return None


def join_camp(camp_id, user_id):
    """الانضمام لمعسكر دراسة"""
    try:
        from study_bot.models import CustomCamp, CampParticipant, User
        
        # التحقق من المعسكر
        camp = CustomCamp.query.get(camp_id)
        if not camp or not camp.is_active:
            logger.error(f"المعسكر {camp_id} غير موجود أو غير نشط")
            return None
        
        # التحقق من المستخدم
        user = User.query.filter_by(telegram_id=user_id).first()
        if not user:
            logger.error(f"المستخدم {user_id} غير موجود")
            return None
        
        # التحقق من عدم تجاوز الحد الأقصى للمشاركين
        if camp.max_participants > 0:
            current_participants = CampParticipant.query.filter_by(
                camp_id=camp.id,
                is_active=True
            ).count()
            
            if current_participants >= camp.max_participants:
                logger.warning(f"تم تجاوز الحد الأقصى للمشاركين ({camp.max_participants}) في المعسكر {camp_id}")
                return None
        
        # التحقق من عدم وجود المستخدم بالفعل في المعسكر
        participant = CampParticipant.query.filter_by(
            camp_id=camp.id,
            user_id=user.id
        ).first()
        
        if participant:
            # إعادة تنشيط المشارك إذا كان غير نشط
            if not participant.is_active:
                participant.is_active = True
                db.session.commit()
                
                logger.info(f"تم إعادة تنشيط المستخدم {user_id} في المعسكر {camp_id}")
                
                # تحديث إعلان المعسكر
                update_camp_announcement(camp.id)
                
                return participant
            
            # المستخدم بالفعل مشارك نشط
            return participant
        
        # إنشاء مشارك جديد
        new_participant = CampParticipant(
            camp_id=camp.id,
            user_id=user.id,
            is_active=True
        )
        
        db.session.add(new_participant)
        db.session.commit()
        
        logger.info(f"تم انضمام المستخدم {user_id} للمعسكر {camp_id}")
        
        # تحديث إعلان المعسكر
        update_camp_announcement(camp.id)
        
        return new_participant
    except Exception as e:
        logger.error(f"خطأ في الانضمام لمعسكر دراسة: {e}")
        logger.error(traceback.format_exc())
        return None


def send_camp_announcement(group_telegram_id, camp):
    """إرسال إعلان عن معسكر جديد"""
    try:
        from study_bot.group_handlers import send_group_message
        from study_bot.group_tasks import MOTIVATIONAL_QUOTES
        
        # إعداد رسالة الإعلان
        announcement = f"""🏕️ <b>معسكر دراسي جديد: {camp.name}</b>

<b>الوصف:</b> {camp.description}

<b>تاريخ البدء:</b> {camp.start_date.strftime('%Y-%m-%d %H:%M')}
<b>تاريخ الانتهاء:</b> {camp.end_date.strftime('%Y-%m-%d %H:%M')}
<b>المشاركون:</b> {camp.get_active_participants_count()}"""
        
        # إضافة الحد الأقصى للمشاركين إذا كان محدد
        if camp.max_participants > 0:
            announcement += f" / {camp.max_participants}"
        
        # إضافة المهام القادمة
        upcoming_tasks = camp.get_next_tasks(3)  # أقرب 3 مهام
        if upcoming_tasks:
            announcement += "\n\n<b>المهام القادمة:</b>"
            for task in upcoming_tasks:
                announcement += f"\n• {task.scheduled_time.strftime('%Y-%m-%d %H:%M')} - {task.title}"
        
        # إضافة اقتباس تحفيزي عشوائي
        announcement += f"\n\n{random.choice(MOTIVATIONAL_QUOTES)}"
        
        # إضافة زر الانضمام
        keyboard = [
            [{'text': '🚀 انضم للمعسكر', 'callback_data': f'join_camp:{camp.id}'}]
        ]
        
        # إرسال الإعلان
        result = send_group_message(group_telegram_id, announcement, {'inline_keyboard': keyboard})
        
        if result:
            # تخزين معرف رسالة الإعلان
            camp.announcement_message_id = result.get('message_id')
            db.session.commit()
            
            logger.info(f"تم إرسال إعلان المعسكر {camp.id} إلى المجموعة {group_telegram_id}")
            
            return True
        else:
            logger.error(f"فشل إرسال إعلان المعسكر {camp.id} إلى المجموعة {group_telegram_id}")
            return False
    except Exception as e:
        logger.error(f"خطأ في إرسال إعلان عن معسكر جديد: {e}")
        logger.error(traceback.format_exc())
        return False


def send_camp_task(task_id):
    """إرسال مهمة من مهام المعسكر"""
    try:
        from study_bot.camp_scheduler import send_camp_task as scheduler_send_task
        return scheduler_send_task(task_id)
    except Exception as e:
        logger.error(f"خطأ في إرسال مهمة من مهام المعسكر: {e}")
        logger.error(traceback.format_exc())
        return False


def handle_camp_join(camp_id, user_id, callback_query_id):
    """معالجة طلب الانضمام لمعسكر"""
    try:
        from study_bot.group_handlers import answer_callback_query
        
        # الانضمام للمعسكر
        participant = join_camp(camp_id, user_id)
        
        if participant:
            # الرد على الاستعلام
            answer_callback_query(callback_query_id, "✅ تم انضمامك للمعسكر بنجاح!", True)
            return True
        else:
            # الرد على الاستعلام بالفشل
            from study_bot.models import CustomCamp
            camp = CustomCamp.query.get(camp_id)
            
            if camp and camp.max_participants > 0:
                current_participants = len(camp.participants)
                if current_participants >= camp.max_participants:
                    answer_callback_query(callback_query_id, "❌ عذراً، المعسكر ممتلئ. تم الوصول للحد الأقصى من المشاركين.", True)
                    return False
            
            answer_callback_query(callback_query_id, "❌ حدث خطأ أثناء الانضمام للمعسكر. الرجاء المحاولة مرة أخرى.", True)
            return False
    except Exception as e:
        logger.error(f"خطأ في معالجة طلب الانضمام لمعسكر: {e}")
        logger.error(traceback.format_exc())
        return False


def handle_camp_task_join(task_id, user_id, callback_query_id):
    """معالجة طلب المشاركة في مهمة معسكر"""
    try:
        from study_bot.models import CampTask, CustomCamp, CampParticipant, User
        from study_bot.group_handlers import answer_callback_query
        
        # التحقق من المهمة
        task = CampTask.query.get(task_id)
        if not task or not task.is_sent:
            answer_callback_query(callback_query_id, "❌ المهمة غير موجودة أو لم يتم إرسالها بعد", True)
            return False
        
        # التحقق من المعسكر
        camp = CustomCamp.query.get(task.camp_id)
        if not camp or not camp.is_active:
            answer_callback_query(callback_query_id, "❌ المعسكر غير نشط أو غير موجود", True)
            return False
        
        # التحقق من المهلة
        if task.is_expired():
            answer_callback_query(callback_query_id, "❌ انتهت مهلة المشاركة في هذه المهمة", True)
            return False
        
        # التحقق من المستخدم
        user = User.query.filter_by(telegram_id=user_id).first()
        if not user:
            answer_callback_query(callback_query_id, "❌ يجب عليك استخدام البوت أولاً", True)
            return False
        
        # التحقق من اشتراك المستخدم في المعسكر
        participant = CampParticipant.query.filter_by(
            camp_id=camp.id,
            user_id=user.id,
            is_active=True
        ).first()
        
        if not participant:
            # محاولة الانضمام للمعسكر تلقائياً
            participant = join_camp(camp.id, user_id)
            
            if not participant:
                answer_callback_query(callback_query_id, "❌ يجب الانضمام للمعسكر أولاً", True)
                return False
        
        # إضافة مشاركة في المهمة
        participation = task.add_participation(participant.id)
        
        if participation:
            # الرد على الاستعلام
            answer_callback_query(callback_query_id, f"✅ تم تسجيل مشاركتك في المهمة! +{task.points} نقطة", True)
            return True
        else:
            # الرد على الاستعلام بالفشل
            answer_callback_query(callback_query_id, "❌ حدث خطأ أثناء تسجيل المشاركة. ربما شاركت في هذه المهمة من قبل.", True)
            return False
    except Exception as e:
        logger.error(f"خطأ في معالجة طلب المشاركة في مهمة معسكر: {e}")
        logger.error(traceback.format_exc())
        return False


def update_camp_announcement(camp_id):
    """تحديث إعلان المعسكر بمعلومات جديدة"""
    try:
        from study_bot.models import CustomCamp, Group
        from study_bot.group_handlers import edit_group_message
        from study_bot.group_tasks import MOTIVATIONAL_QUOTES
        
        # التحقق من المعسكر
        camp = CustomCamp.query.get(camp_id)
        if not camp or not camp.is_active:
            logger.error(f"المعسكر {camp_id} غير موجود أو غير نشط")
            return False
        
        # التحقق من وجود معرف رسالة الإعلان
        if not camp.announcement_message_id:
            logger.warning(f"لا يوجد معرف لرسالة إعلان المعسكر {camp_id}")
            
            # محاولة إرسال إعلان جديد
            group = Group.query.get(camp.group_id)
            if group:
                return send_camp_announcement(group.telegram_id, camp)
            
            return False
        
        # الحصول على المجموعة
        group = Group.query.get(camp.group_id)
        if not group or not group.is_active:
            logger.error(f"المجموعة {camp.group_id} غير موجودة أو غير نشطة")
            return False
        
        # إعداد رسالة الإعلان المحدثة
        announcement = f"""🏕️ <b>معسكر دراسي: {camp.name}</b>

<b>الوصف:</b> {camp.description}

<b>تاريخ البدء:</b> {camp.start_date.strftime('%Y-%m-%d %H:%M')}
<b>تاريخ الانتهاء:</b> {camp.end_date.strftime('%Y-%m-%d %H:%M')}
<b>المشاركون:</b> {camp.get_active_participants_count()}"""
        
        # إضافة الحد الأقصى للمشاركين إذا كان محدد
        if camp.max_participants > 0:
            announcement += f" / {camp.max_participants}"
        
        # إضافة المهام القادمة
        upcoming_tasks = camp.get_next_tasks(3)  # أقرب 3 مهام
        if upcoming_tasks:
            announcement += "\n\n<b>المهام القادمة:</b>"
            for task in upcoming_tasks:
                announcement += f"\n• {task.scheduled_time.strftime('%Y-%m-%d %H:%M')} - {task.title}"
        
        # إضافة أفضل المشاركين
        top_participants = camp.get_top_participants(3)  # أفضل 3 مشاركين
        if top_participants:
            announcement += "\n\n<b>أفضل المشاركين:</b>"
            for i, participant in enumerate(top_participants):
                from study_bot.models import User
                user = User.query.get(participant.user_id)
                if user:
                    username = user.display_name
                    announcement += f"\n{i+1}. {username}: {participant.total_points} نقطة"
        
        # إضافة اقتباس تحفيزي عشوائي
        announcement += f"\n\n{random.choice(MOTIVATIONAL_QUOTES)}"
        
        # إضافة زر الانضمام
        keyboard = [
            [{'text': '🚀 انضم للمعسكر', 'callback_data': f'join_camp:{camp.id}'}]
        ]
        
        # تحديث الإعلان
        result = edit_group_message(
            group.telegram_id,
            camp.announcement_message_id,
            announcement,
            {'inline_keyboard': keyboard}
        )
        
        if result:
            logger.info(f"تم تحديث إعلان المعسكر {camp.id} في المجموعة {group.telegram_id}")
            return True
        else:
            logger.error(f"فشل تحديث إعلان المعسكر {camp.id} في المجموعة {group.telegram_id}")
            
            # محاولة إرسال إعلان جديد
            return send_camp_announcement(group.telegram_id, camp)
    except Exception as e:
        logger.error(f"خطأ في تحديث إعلان المعسكر: {e}")
        logger.error(traceback.format_exc())
        return False


def send_camp_report(camp_id):
    """إرسال تقرير عن أداء المعسكر"""
    try:
        from study_bot.camp_scheduler import send_camp_daily_report
        return send_camp_daily_report(camp_id)
    except Exception as e:
        logger.error(f"خطأ في إرسال تقرير عن أداء المعسكر: {e}")
        logger.error(traceback.format_exc())
        return False


def handle_create_camp_command(group_id, admin_id, command_text):
    """معالجة أمر إنشاء معسكر جديد"""
    try:
        # التحقق من صحة الأمر
        # صيغة الأمر: /createcamp اسم المعسكر | وصف المعسكر | تاريخ البدء | تاريخ الانتهاء | الحد الأقصى للمشاركين
        command_pattern = r'/createcamp\s+(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)(?:\s*\|\s*(\d+))?$'
        match = re.match(command_pattern, command_text, re.DOTALL)
        
        if not match:
            return "❌ صيغة الأمر غير صحيحة. يجب أن تكون:\n/createcamp اسم المعسكر | وصف المعسكر | تاريخ البدء | تاريخ الانتهاء | الحد الأقصى للمشاركين"
        
        camp_name = match.group(1).strip()
        description = match.group(2).strip()
        start_date_str = match.group(3).strip()
        end_date_str = match.group(4).strip()
        max_participants_str = match.group(5).strip() if match.group(5) else "0"
        
        # التحقق من صحة التواريخ
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d %H:%M")
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d %H:%M")
        except ValueError:
            return "❌ صيغة التاريخ غير صحيحة. يجب أن تكون: YYYY-MM-DD HH:MM"
        
        # التحقق من صحة الحد الأقصى للمشاركين
        try:
            max_participants = int(max_participants_str)
            if max_participants < 0:
                max_participants = 0
        except ValueError:
            return "❌ الحد الأقصى للمشاركين يجب أن يكون رقمًا صحيحًا"
        
        # إنشاء المعسكر
        camp = create_custom_camp(
            group_id,
            admin_id,
            camp_name,
            description,
            start_date,
            end_date,
            max_participants
        )
        
        if camp:
            return f"✅ تم إنشاء المعسكر \"{camp_name}\" بنجاح!\n\nالمعرف: {camp.id}\nتاريخ البدء: {start_date_str}\nتاريخ الانتهاء: {end_date_str}"
        else:
            return "❌ فشل إنشاء المعسكر. يرجى التحقق من المعلومات والمحاولة مرة أخرى."
    except Exception as e:
        logger.error(f"خطأ في معالجة أمر إنشاء معسكر جديد: {e}")
        logger.error(traceback.format_exc())
        return f"❌ حدث خطأ أثناء معالجة الأمر: {str(e)}"


def handle_add_camp_task_command(group_id, admin_id, command_text):
    """معالجة أمر إضافة مهمة لمعسكر"""
    try:
        # التحقق من صحة الأمر
        # صيغة الأمر: /addtask معرف المعسكر | عنوان المهمة | وصف المهمة | وقت المهمة | النقاط | المهلة بالدقائق
        command_pattern = r'/addtask\s+(\d+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(\d+)(?:\s*\|\s*(\d+))?$'
        match = re.match(command_pattern, command_text, re.DOTALL)
        
        if not match:
            return "❌ صيغة الأمر غير صحيحة. يجب أن تكون:\n/addtask معرف المعسكر | عنوان المهمة | وصف المهمة | وقت المهمة | النقاط | المهلة بالدقائق"
        
        camp_id = int(match.group(1).strip())
        task_title = match.group(2).strip()
        task_description = match.group(3).strip()
        scheduled_time_str = match.group(4).strip()
        points_str = match.group(5).strip()
        deadline_minutes_str = match.group(6).strip() if match.group(6) else "10"
        
        # التحقق من صحة الوقت
        try:
            scheduled_time = datetime.strptime(scheduled_time_str, "%Y-%m-%d %H:%M")
        except ValueError:
            return "❌ صيغة الوقت غير صحيحة. يجب أن تكون: YYYY-MM-DD HH:MM"
        
        # التحقق من صحة النقاط
        try:
            points = int(points_str)
            if points < 1:
                points = 1
            elif points > 10:
                points = 10
        except ValueError:
            return "❌ النقاط يجب أن تكون رقمًا صحيحًا بين 1 و 10"
        
        # التحقق من صحة المهلة
        try:
            deadline_minutes = int(deadline_minutes_str)
            if deadline_minutes < 1:
                deadline_minutes = 1
        except ValueError:
            return "❌ المهلة يجب أن تكون رقمًا صحيحًا أكبر من 0"
        
        # التحقق من المعسكر
        from study_bot.models import CustomCamp, Group
        
        camp = CustomCamp.query.get(camp_id)
        if not camp:
            return f"❌ المعسكر بالمعرف {camp_id} غير موجود"
        
        if not camp.is_active:
            return f"❌ المعسكر \"{camp.name}\" غير نشط"
        
        # التحقق من أن المعسكر في نفس المجموعة
        camp_group = Group.query.get(camp.group_id)
        if camp_group.telegram_id != group_id:
            return f"❌ المعسكر \"{camp.name}\" ليس في هذه المجموعة"
        
        # إضافة المهمة
        task = add_camp_task(
            camp_id,
            admin_id,
            task_title,
            task_description,
            scheduled_time,
            points,
            deadline_minutes
        )
        
        if task:
            return f"✅ تمت إضافة المهمة \"{task_title}\" بنجاح للمعسكر \"{camp.name}\"!\n\nالمعرف: {task.id}\nالوقت: {scheduled_time_str}\nالنقاط: {points}\nالمهلة: {deadline_minutes} دقيقة"
        else:
            return "❌ فشل إضافة المهمة. يرجى التحقق من المعلومات والمحاولة مرة أخرى."
    except Exception as e:
        logger.error(f"خطأ في معالجة أمر إضافة مهمة لمعسكر: {e}")
        logger.error(traceback.format_exc())
        return f"❌ حدث خطأ أثناء معالجة الأمر: {str(e)}"


def check_scheduled_camp_tasks():
    """فحص وإرسال مهام المعسكرات المجدولة"""
    try:
        from study_bot.camp_scheduler import check_and_send_scheduled_camp_tasks
        return check_and_send_scheduled_camp_tasks()
    except Exception as e:
        logger.error(f"خطأ في فحص وإرسال مهام المعسكرات المجدولة: {e}")
        logger.error(traceback.format_exc())
        return 0


def send_camp_reports():
    """إرسال تقارير يومية للمعسكرات النشطة"""
    try:
        from study_bot.camp_scheduler import generate_camp_daily_report
        return generate_camp_daily_report()
    except Exception as e:
        logger.error(f"خطأ في إرسال تقارير يومية للمعسكرات النشطة: {e}")
        logger.error(traceback.format_exc())
        return 0


def handle_camp_report_command(group_id, admin_id, command_text):
    """معالجة أمر طلب تقرير المعسكر"""
    try:
        # التحقق من صحة الأمر
        # صيغة الأمر: /campreport معرف المعسكر
        command_pattern = r'/campreport\s+(\d+)$'
        match = re.match(command_pattern, command_text)
        
        if not match:
            return "❌ صيغة الأمر غير صحيحة. يجب أن تكون:\n/campreport معرف المعسكر"
        
        camp_id = int(match.group(1).strip())
        
        # التحقق من المعسكر
        from study_bot.models import CustomCamp, Group
        
        camp = CustomCamp.query.get(camp_id)
        if not camp:
            return f"❌ المعسكر بالمعرف {camp_id} غير موجود"
        
        # التحقق من أن المعسكر في نفس المجموعة
        camp_group = Group.query.get(camp.group_id)
        if camp_group.telegram_id != group_id:
            return f"❌ المعسكر \"{camp.name}\" ليس في هذه المجموعة"
        
        # إرسال التقرير
        result = send_camp_report(camp_id)
        
        if result:
            return None  # لا داعي لإرسال رد، تم إرسال التقرير بالفعل
        else:
            return "❌ فشل إرسال تقرير المعسكر. يرجى المحاولة مرة أخرى."
    except Exception as e:
        logger.error(f"خطأ في معالجة أمر طلب تقرير المعسكر: {e}")
        logger.error(traceback.format_exc())
        return f"❌ حدث خطأ أثناء معالجة الأمر: {str(e)}"