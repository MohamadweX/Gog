"""
معسكرات الدراسة المخصصة
يحتوي على وظائف لإدارة معسكرات الدراسة المخصصة التي ينشئها مشرفو المجموعات
"""

import json
import random
from datetime import datetime, timedelta

from study_bot.config import TELEGRAM_API_URL, TELEGRAM_BOT_TOKEN, logger
from study_bot.models import User, Group, GroupParticipant, db
from study_bot.models.camps_models import CustomCamp, CampTask, CampParticipant, CampTaskParticipation
from study_bot.group_tasks import MOTIVATIONAL_QUOTES


# إرسال رسالة إلى مجموعة
def send_group_message(chat_id, text, reply_markup=None, parse_mode="HTML"):
    """إرسال رسالة إلى مجموعة"""
    import requests
    
    url = f"{TELEGRAM_API_URL}/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode
    }
    
    if reply_markup:
        data["reply_markup"] = reply_markup if isinstance(reply_markup, str) else json.dumps(reply_markup)
    
    try:
        response = requests.post(url, json=data, timeout=60)
        if response.status_code == 200:
            return response.json().get("result")
        else:
            logger.error(f"فشل في إرسال رسالة للمجموعة {chat_id}: {response.text}")
            return None
    except Exception as e:
        logger.error(f"خطأ أثناء إرسال رسالة للمجموعة {chat_id}: {e}")
        return None


# إرسال استجابة للضغط على زر
def answer_callback_query(callback_query_id, text=None, show_alert=False):
    """الإجابة على نداء الاستجابة"""
    import requests
    
    url = f"{TELEGRAM_API_URL}/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
    data = {
        "callback_query_id": callback_query_id
    }
    
    if text:
        data["text"] = text
    
    data["show_alert"] = show_alert
    
    try:
        response = requests.post(url, json=data, timeout=60)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"فشل في الإجابة على نداء الاستجابة: {response.text}")
            return None
    except Exception as e:
        logger.error(f"خطأ في الإجابة على نداء الاستجابة: {e}")
        return None


# تعديل رسالة في مجموعة
def edit_group_message(chat_id, message_id, text, reply_markup=None, parse_mode="HTML"):
    """تعديل رسالة في المجموعة"""
    try:
        # استدعاء الدالة المركزية لتعديل الرسائل
        from study_bot.bot import edit_message
        
        result = edit_message(chat_id, message_id, text, reply_markup, parse_mode)
        return result
    except Exception as e:
        logger.error(f"خطأ أثناء تعديل رسالة في المجموعة {chat_id}: {e}")
        return None


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
        user = User.get_or_create(user_id)
        existing_participant = CampParticipant.query.filter_by(camp_id=camp.id, user_id=user.id, is_active=True).first()
        if existing_participant:
            answer_callback_query(callback_query_id, "✅ أنت منضم بالفعل لهذا المعسكر!")
            return True
        
        # إنشاء مشارك جديد
        participant = join_camp(camp.id, user.id)
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
        user = User.get_or_create(user_id)
        participant = CampParticipant.query.filter_by(camp_id=camp.id, user_id=user.id, is_active=True).first()
        if not participant:
            answer_callback_query(callback_query_id, "❌ يجب أن تنضم للمعسكر أولاً")
            return False
        
        # التحقق من عدم المشاركة سابقاً
        existing_participation = CampTaskParticipation.query.filter_by(
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
        
        # حساب عدد المشاركين
        participants = CampParticipant.query.filter_by(camp_id=camp.id, is_active=True).all()
        participants_count = len(participants)
        
        # إعداد نص التقرير
        today_date = datetime.utcnow().strftime('%Y-%m-%d')
        
        text = f"""
📊 <b>تقرير معسكر {camp.name}</b> - {today_date}

👥 عدد المشاركين: {participants_count}"""
        
        if camp.max_participants > 0:
            text += f" / {camp.max_participants}"
            
        # إضافة قائمة بأفضل المشاركين
        if participants:
            # ترتيب المشاركين حسب النقاط
            top_participants = sorted(participants, key=lambda p: p.total_points, reverse=True)[:5]
            
            if top_participants:
                text += "\n\n🏆 <b>أفضل المشاركين:</b>"
                
                for i, p in enumerate(top_participants):
                    user = User.query.get(p.user_id)
                    if user:
                        user_name = user.get_full_name() or f"المستخدم {user.telegram_id}"
                        text += f"\n{i+1}. {user_name}: {p.total_points} نقطة"
        
        # إضافة اقتباس تحفيزي
        motivation = random.choice(MOTIVATIONAL_QUOTES)
        text += f"\n\n✨ {motivation}"
        
        # إرسال التقرير
        message = send_group_message(group.telegram_id, text)
        if message:
            logger.info(f"تم إرسال تقرير المعسكر {camp.name} إلى المجموعة {group.telegram_id}")
            return message
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
        # الصيغة المتوقعة: /newcamp اسم المعسكر | وصف المعسكر | YYYY-MM-DD | YYYY-MM-DD | [عدد المشاركين]
        
        # تجاهل كلمة الأمر نفسها وأخذ المحتوى فقط
        if command_text.startswith('/newcamp'):
            command_text = command_text[len('/newcamp'):].strip()
            
        params = command_text.strip().split('|')
        if len(params) < 4:
            return """❌ صيغة غير صحيحة. الرجاء استخدام:
/newcamp اسم المعسكر | وصف المعسكر | تاريخ البداية YYYY-MM-DD | تاريخ النهاية YYYY-MM-DD | [الحد الأقصى للمشاركين]

مثال:
/newcamp معسكر الرياضيات | مراجعة مكثفة للرياضيات | 2025-06-01 | 2025-06-30 | 20"""
        
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
            return f"✅ تم إنشاء معسكر '{camp.name}' بنجاح! تحقق من إعلان المعسكر في المجموعة."
        else:
            return "❌ حدث خطأ أثناء إنشاء المعسكر. يرجى المحاولة مرة أخرى."
    except Exception as e:
        logger.error(f"خطأ في معالجة أمر إنشاء معسكر: {e}")
        return "❌ حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى."


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
        
        # تجاهل كلمة الأمر نفسها وأخذ المحتوى فقط
        if command_text.startswith('/addtask'):
            command_text = command_text[len('/addtask'):].strip()
            
        # تحليل نص الأمر
        params = command_text.strip().split('|')
        if len(params) < 5:
            return """❌ صيغة غير صحيحة. الرجاء استخدام:
/addtask <رقم المعسكر> | <عنوان المهمة> | <وصف المهمة> | <وقت الجدولة YYYY-MM-DD HH:MM> | <النقاط> | [مهلة بالدقائق]

مثال:
/addtask 1 | مراجعة الفصل الأول | راجع الصفحات 10-20 | 2025-06-01 10:00 | 5 | 30"""
        
        # الحصول على المعلومات
        try:
            camp_id = int(params[0].strip())
        except ValueError:
            return "❌ رقم المعسكر يجب أن يكون عددًا صحيحًا"
            
        # التحقق من المعسكر
        camp = CustomCamp.query.get(camp_id)
        if not camp or camp.group_id != group.id:
            return "❌ لم يتم العثور على المعسكر المطلوب"
            
        # التحقق من المشرف
        if admin_id != camp.created_by:
            return "❌ هذا الأمر متاح فقط لمشرف المعسكر"
        
        # الحصول على بيانات المهمة
        task_title = params[1].strip()
        task_description = params[2].strip()
        
        # تحليل وقت الجدولة
        try:
            scheduled_time = datetime.strptime(params[3].strip(), '%Y-%m-%d %H:%M')
        except ValueError:
            return "❌ صيغة وقت الجدولة غير صحيحة. يرجى استخدام الصيغة: YYYY-MM-DD HH:MM"
            
        # التحقق من النقاط
        try:
            points = int(params[4].strip())
            if points <= 0:
                return "❌ يجب أن تكون النقاط عدداً موجباً"
        except ValueError:
            return "❌ يجب أن تكون النقاط عدداً صحيحاً"
        
        # المهلة (اختيارية)
        deadline_minutes = 10
        if len(params) > 5:
            try:
                deadline_minutes = int(params[5].strip())
                if deadline_minutes <= 0:
                    return "❌ يجب أن تكون المهلة عدداً موجباً من الدقائق"
            except ValueError:
                return "❌ يجب أن تكون المهلة عدداً صحيحاً"
        
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
            formatted_time = scheduled_time.strftime('%Y-%m-%d %H:%M')
            return f"✅ تم إضافة المهمة '{task.title}' بنجاح للمعسكر {camp.name}.\nوقت الجدولة: {formatted_time}\nالنقاط: {points}\nالمهلة: {deadline_minutes} دقيقة"
        else:
            return "❌ حدث خطأ أثناء إضافة المهمة. يرجى المحاولة مرة أخرى."
    except Exception as e:
        logger.error(f"خطأ في معالجة أمر إضافة مهمة لمعسكر: {e}")
        return "❌ حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى."


# فحص المهام المجدولة وإرسالها
def check_scheduled_camp_tasks():
    """فحص وإرسال مهام المعسكرات المجدولة"""
    try:
        # الحصول على الوقت الحالي
        now = datetime.utcnow()
        
        # البحث عن مهام معسكرات لم ترسل بعد وحان وقتها
        tasks = CampTask.query.filter(
            CampTask.is_sent == False,
            CampTask.scheduled_time <= now
        ).all()
        
        # إرسال كل مهمة
        for task in tasks:
            # التحقق من أن المعسكر نشط
            camp = CustomCamp.query.get(task.camp_id)
            if not camp or not camp.is_active:
                continue
                
            # التحقق من أن المعسكر في الفترة النشطة
            today = now.date()
            if today < camp.start_date.date() or today > camp.end_date.date():
                continue
            
            # إرسال المهمة
            send_camp_task(task.id)
        
        # تسجيل نتيجة الفحص
        logger.info(f"تم فحص وإرسال {len(tasks)} مهمة معسكر مجدولة")
    except Exception as e:
        logger.error(f"خطأ في فحص وإرسال مهام المعسكرات المجدولة: {e}")


# إرسال تقارير يومية للمعسكرات
def send_camp_reports():
    """إرسال تقارير يومية للمعسكرات النشطة"""
    try:
        # الحصول على الوقت الحالي
        now = datetime.utcnow()
        
        # البحث عن معسكرات نشطة
        camps = CustomCamp.query.filter(
            CustomCamp.is_active == True,
            CustomCamp.start_date <= now,
            CustomCamp.end_date >= now
        ).all()
        
        # إرسال تقرير لكل معسكر
        for camp in camps:
            send_camp_report(camp.id)
        
        # تسجيل نتيجة الإرسال
        logger.info(f"تم إرسال {len(camps)} تقرير يومي للمعسكرات النشطة")
    except Exception as e:
        logger.error(f"خطأ في إرسال التقارير اليومية للمعسكرات: {e}")


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
        
        # تجاهل كلمة الأمر نفسها وأخذ المحتوى فقط
        if command_text.startswith('/campreport'):
            command_text = command_text[len('/campreport'):].strip()
            
        # تحليل نص الأمر
        params = command_text.strip().split()
        if len(params) < 1:
            return """❌ صيغة غير صحيحة. الرجاء استخدام:
/campreport <رقم المعسكر>

مثال:
/campreport 1"""
        
        # الحصول على رقم المعسكر
        try:
            camp_id = int(params[0])
        except ValueError:
            return "❌ رقم المعسكر يجب أن يكون عددًا صحيحًا"
            
        # التحقق من المعسكر
        camp = CustomCamp.query.get(camp_id)
        if not camp or camp.group_id != group.id:
            return "❌ لم يتم العثور على المعسكر المطلوب"
        
        # إرسال التقرير
        message = send_camp_report(camp.id)
        if message:
            return f"✅ تم إرسال تقرير المعسكر '{camp.name}' بنجاح!"
        else:
            return "❌ حدث خطأ أثناء إرسال التقرير. يرجى المحاولة مرة أخرى."
    except Exception as e:
        logger.error(f"خطأ في معالجة أمر طلب تقرير المعسكر: {e}")
        return "❌ حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى."


# معالجة الاستجابات للأزرار في واجهة المعسكرات
def handle_camp_callback_query(callback_data, user_id, callback_query_id):
    """معالجة استجابات أزرار المعسكرات"""
    try:
        # تقسيم بيانات الاستجابة
        parts = callback_data.split(':')
        if len(parts) != 2:
            answer_callback_query(callback_query_id, "❌ بيانات غير صالحة")
            return False
        
        action = parts[0]
        data_id = int(parts[1])
        
        # معالجة الانضمام للمعسكر
        if action == "camp_join":
            return handle_camp_join(data_id, user_id, callback_query_id)
        
        # معالجة المشاركة في مهمة معسكر
        elif action == "camp_task_join":
            return handle_camp_task_join(data_id, user_id, callback_query_id)
        
        # استجابة غير معروفة
        else:
            answer_callback_query(callback_query_id, f"❌ إجراء غير معروف: {action}")
            return False
    except Exception as e:
        logger.error(f"خطأ في معالجة استجابات أزرار المعسكرات: {e}")
        answer_callback_query(callback_query_id, "❌ حدث خطأ أثناء معالجة طلبك")
        return False