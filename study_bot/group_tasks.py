#!/usr/bin/env python3
"""
وحدة مهام المجموعات
تحتوي على وظائف للتعامل مع مهام المجموعات ذات المهلة الزمنية
تم تطويره ليشمل جداول صباحية ومسائية متكاملة
"""

import random
import logging
import requests
from datetime import datetime, timedelta

from study_bot.config import logger, TELEGRAM_API_URL, get_current_time
from study_bot.models import db, User, Group, GroupScheduleTracker, GroupTaskTracker, MotivationalMessage
from study_bot.models.group import GroupTaskParticipant, GroupTaskParticipation

# دالة لإرسال رسالة إلى المستخدم أو المجموعة
def send_message(chat_id, text, reply_markup=None, parse_mode='HTML'):
    """إرسال رسالة إلى مستخدم أو مجموعة"""
    try:
        # بناء رابط API
        url = f"{TELEGRAM_API_URL}/sendMessage"
        
        # بناء البيانات
        data = {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": True
        }
        
        if reply_markup:
            data["reply_markup"] = reply_markup
            
        if parse_mode:
            data["parse_mode"] = parse_mode
        
        # إرسال الطلب
        response = requests.post(url, json=data)
        response_data = response.json()
        
        if not response_data.get('ok', False):
            logger.error(f"خطأ في إرسال الرسالة: {response_data}")
            return None
        
        return response_data.get('result')
    except Exception as e:
        logger.error(f"خطأ في إرسال الرسالة: {e}")
        return None

# الإجابة على نداء الاستجابة
def answer_callback_query(callback_query_id, text=None, show_alert=False):
    """الإجابة على نداء الاستجابة"""
    try:
        import requests
        from study_bot.config import TELEGRAM_API_URL
        
        # بناء رابط API
        url = f"{TELEGRAM_API_URL}/answerCallbackQuery"
        
        # بناء البيانات
        data = {
            "callback_query_id": callback_query_id,
            "cache_time": 0
        }
        
        if text:
            data["text"] = text
            
        if show_alert:
            data["show_alert"] = True
        
        # إرسال الطلب
        response = requests.post(url, json=data)
        response_data = response.json()
        
        if not response_data.get('ok', False):
            logger.error(f"خطأ في الإجابة على نداء الاستجابة: {response_data}")
            return False
            
        return True
    except Exception as e:
        logger.error(f"خطأ في الإجابة على نداء الاستجابة: {e}")
        return False

# تحفيزات إضافية للعرض مع المهام
MOTIVATIONAL_QUOTES = [
    "امضِ قدماً، حتى عندما تكون الخطوة صعبة والطريق طويلة.",
    "النجاح ليس نهائياً، والفشل ليس قاتلاً، الشجاعة للمواصلة هي ما يهم.",
    "المذاكرة اليوم تعني النجاح غداً.",
    "من تعب ساعة تنعم ألف ساعة.",
    "ليس المهم أن تبدأ بقوة، الأهم أن تستمر بعزيمة.",
    "العلم نور، والتركيز مفتاحه.",
    "الاستثمار في العلم يعطي أفضل الفوائد.",
    "رغم التعب والسهر، ستبقى الفرحة أكبر.",
    "جبال النجاح لا يمكن تسلقها بأيدي في الجيوب.",
    "لا وقت للكسل، كل دقيقة لها ثمن."
]

# استيراد قائمة مهام المعسكرات من ملف جدولة المعسكرات
from study_bot.camp_scheduler import MORNING_REMINDERS, EVENING_REMINDERS

# تحويل المهام من التنسيق الجديد إلى التنسيق القديم
MORNING_SCHEDULE = []
for i, reminder in enumerate(MORNING_REMINDERS):
    time_str = reminder[0]
    task_name = f"morning_task_{i}"
    message_text = reminder[1]
    points = reminder[2]
    MORNING_SCHEDULE.append((time_str, task_name, message_text, points))

# تحويل المهام المسائية من التنسيق الجديد إلى التنسيق القديم
EVENING_SCHEDULE = []
for i, reminder in enumerate(EVENING_REMINDERS):
    time_str = reminder[0]
    task_name = f"evening_task_{i}"
    message_text = reminder[1]
    points = reminder[2]
    EVENING_SCHEDULE.append((time_str, task_name, message_text, points))

# نقاط المهام للجداول
MORNING_POINTS = 2
EVENING_POINTS = 2

# إرسال رسالة الجدول الصباحي للمجموعة
def send_group_morning_message(group_telegram_id):
    """إرسال رسالة الجدول الصباحي للمجموعة"""
    try:
        # اختيار اقتباس تحفيزي عشوائي
        motivation = random.choice(MOTIVATIONAL_QUOTES)
        
        # إنشاء رسالة الترحيب
        welcome_text = f"""
📅 ╭──────────────────────╮
      جدول المعسكر الصباحي
╰──────────────────────╯

مرحباً بكم في معسكر الدراسة الصباحي!
لنبدأ يوماً مليئاً بالإنجاز والتركيز 🌟

⏰ المهام القادمة خلال اليوم:
🔸 الفجر 04:25
🔸 المذاكرة 08:30
🔸 الظهر 12:51 
🔸 العصر 16:28
🔸 المغرب 19:39
🔸 العشاء 21:06

🔖 {motivation}

هيا بنا نبدأ! 💪
"""
        
        # إضافة زر للانضمام للمعسكر
        keyboard = {
            "inline_keyboard": [
                [{
                    "text": "✅ انضم للمعسكر الصباحي",
                    "callback_data": "join_morning_camp"
                }]
            ]
        }
        
        # إرسال الرسالة
        result = send_message(group_telegram_id, welcome_text, reply_markup=keyboard, parse_mode="HTML")
        logger.info(f"تم إرسال رسالة الجدول الصباحي للمجموعة {group_telegram_id}")
        return result
    except Exception as e:
        logger.error(f"خطأ في إرسال رسالة الجدول الصباحي للمجموعة {group_telegram_id}: {e}")
        return None


# إرسال رسالة الجدول المسائي للمجموعة
def send_group_evening_message(group_telegram_id):
    """إرسال رسالة الجدول المسائي للمجموعة"""
    try:
        # اختيار اقتباس تحفيزي عشوائي
        motivation = random.choice(MOTIVATIONAL_QUOTES)
        
        # إنشاء رسالة الترحيب
        welcome_text = f"""
🌃 ╭──────────────────────╮
      جدول المعسكر المسائي
╰──────────────────────╯

مرحباً بكم في معسكر الدراسة المسائي!
وقت المذاكرة المركزة والإنجازات العظيمة 🌟

⏰ المهام القادمة خلال الليل:
🔸 البداية 16:00
🔸 العشاء 20:00
🔸 الدراسة 20:30
🔸 العشاء 21:10
🔸 استراحة 01:00
🔸 تقييم 04:05
🔸 الفجر 04:25

🔖 {motivation}

هيا بنا نبدأ! 💪
"""
        
        # إضافة زر للانضمام للمعسكر
        keyboard = {
            "inline_keyboard": [
                [{
                    "text": "✅ انضم للمعسكر المسائي",
                    "callback_data": "join_evening_camp"
                }]
            ]
        }
        
        # إرسال الرسالة
        result = send_message(group_telegram_id, welcome_text, reply_markup=keyboard, parse_mode="HTML")
        logger.info(f"تم إرسال رسالة الجدول المسائي للمجموعة {group_telegram_id}")
        return result
    except Exception as e:
        logger.error(f"خطأ في إرسال رسالة الجدول المسائي للمجموعة {group_telegram_id}: {e}")
        return None


# إرسال رسالة تحفيزية للمجموعة
def send_motivation_to_group(group_telegram_id):
    """إرسال رسالة تحفيزية للمجموعة"""
    try:
        # الحصول على رسالة تحفيزية عشوائية من قاعدة البيانات
        motivational_message = MotivationalMessage.query.order_by(db.func.random()).first()
        
        # إذا لم يتم العثور على رسائل في قاعدة البيانات، استخدم الرسائل المضمنة
        if not motivational_message:
            motivation_text = random.choice(MOTIVATIONAL_QUOTES)
        else:
            motivation_text = motivational_message.message
        
        # إنشاء رسالة تحفيزية كاملة
        full_text = f"""
✨ <b>رسالة تحفيزية:</b>

"{motivation_text}"

🔥 استمر في التقدم! الإنجاز ينتظرك.
"""
        
        # إرسال الرسالة
        result = send_message(group_telegram_id, full_text, parse_mode="HTML")
        logger.info(f"تم إرسال رسالة تحفيزية للمجموعة {group_telegram_id}")
        return result
    except Exception as e:
        logger.error(f"خطأ في إرسال رسالة تحفيزية للمجموعة {group_telegram_id}: {e}")
        return None


# إرسال رسالة تحفيزية (موجهة من خارج الملف)
def send_motivational_quote(group_id):
    """إرسال رسالة تحفيزية للمجموعة"""
    try:
        # الحصول على المجموعة من قاعدة البيانات
        group = Group.query.get(group_id)
        if not group:
            logger.error(f"لم يتم العثور على المجموعة {group_id}")
            return False
            
        # إرسال الرسالة التحفيزية
        result = send_motivation_to_group(group.telegram_id)
        return result is not None
    except Exception as e:
        logger.error(f"خطأ في إرسال رسالة تحفيزية للمجموعة {group_id}: {e}")
        return False


# إضافة مستخدم إلى جدول المجموعة
def add_user_to_schedule(group_id, user_id, schedule_type):
    """إضافة مستخدم إلى جدول المجموعة"""
    try:
        # الحصول على بيانات المستخدم
        user = User.get_or_create(user_id)
        
        # الحصول على بيانات المجموعة
        group = Group.query.get(group_id)
        if not group:
            logger.error(f"لم يتم العثور على المجموعة {group_id}")
            return False
            
        # إضافة المستخدم كمشارك في المجموعة
        group_participant = GroupTaskParticipant.get_or_create(group.id, user.id)
        
        # الحصول على تتبع جدول المجموعة ليوم اليوم
        schedule = GroupScheduleTracker.get_or_create_for_today(group.id, schedule_type)
        
        # تعيين المستخدم كمشارك في الجدول
        schedule.add_participant(user.id)
        
        logger.info(f"تم إضافة المستخدم {user_id} إلى الجدول {schedule_type} للمجموعة {group_id}")
        return True
    except Exception as e:
        logger.error(f"خطأ في إضافة المستخدم {user_id} إلى الجدول {schedule_type} للمجموعة {group_id}: {e}")
        return False


# إرسال رسالة مهمة مع مهلة زمنية للمشاركة
def send_group_task_message(group_id, task_type, text, points=1, deadline_minutes=10):
    """إرسال رسالة مهمة للمجموعة مع زر للمشاركة ومهلة زمنية"""
    try:
        # الحصول على المجموعة من قاعدة البيانات
        group = Group.query.get(group_id)
        if not group:
            logger.error(f"لم يتم العثور على المجموعة {group_id}")
            return None
            
        # الحصول على تتبع جدول المجموعة ليوم اليوم
        schedule_type = 'morning' if group.morning_schedule_enabled else 'evening' if group.evening_schedule_enabled else 'custom'
        schedule = GroupScheduleTracker.get_or_create_for_today(group_id, schedule_type)
        
        # إضافة زر للمشاركة في المهمة
        deadline_text = f"⏰ يمكنك الانضمام خلال {deadline_minutes} دقائق فقط"
        
        # إضافة معلومات النقاط
        points_text = f"🏆 ستحصل على {points} نقاط عند المشاركة"
        
        # إنشاء نص الرسالة الكامل
        full_text = f"{text}\n\n{deadline_text}\n{points_text}"
        
        # إنشاء زر المشاركة
        keyboard = {
            "inline_keyboard": [
                [{
                    "text": "✅ انضم للمهمة",
                    "callback_data": f"task_join:{task_type}:{schedule.id}"
                }]
            ]
        }
        
        # إرسال الرسالة
        message = send_message(group.telegram_id, full_text, reply_markup=keyboard, parse_mode="HTML")
        if not message:
            logger.error(f"فشل إرسال رسالة المهمة للمجموعة {group.telegram_id}")
            return None
            
        # إنشاء سجل المهمة في قاعدة البيانات
        task = GroupTaskTracker.create_task(
            schedule_id=schedule.id,
            task_type=task_type,
            message_id=message.get('message_id'),
            deadline_minutes=deadline_minutes,
            points=points
        )
        
        logger.info(f"تم إرسال رسالة المهمة {task_type} للمجموعة {group.telegram_id}")
        return task
    except Exception as e:
        logger.error(f"خطأ في إرسال رسالة المهمة {task_type} للمجموعة {group_id}: {e}")
        return None


# معالجة طلب الانضمام لمهمة
def handle_task_join(task_type, schedule_id, user_id, chat_id, callback_query_id):
    """معالجة طلب الانضمام لمهمة"""
    try:
        # الحصول على المهمة من قاعدة البيانات
        schedule_id = int(schedule_id)
        task = GroupTaskTracker.query.filter_by(schedule_id=schedule_id, task_type=task_type).first()
        
        if not task:
            logger.error(f"لم يتم العثور على المهمة {task_type} للجدول {schedule_id}")
            answer_callback_query(callback_query_id, "❌ لم يتم العثور على المهمة المحددة.", True)
            return False
            
        # تحقق من المهلة الزمنية
        if not task.is_active():
            answer_callback_query(callback_query_id, "⏰ انتهت المهلة المحددة للمهمة.", True)
            return False
        
        # الحصول على بيانات المستخدم
        user = User.get_or_create(user_id)
        
        # تحقق مما إذا كان المستخدم قد انضم بالفعل
        if task.has_user_joined(user.id):
            answer_callback_query(callback_query_id, "✅ أنت منضم بالفعل لهذه المهمة!", True)
            return True
        
        # إضافة المستخدم إلى المهمة
        success = task.add_participant(user.id)
        if success:
            # حساب النقاط بناءً على نوع الجدول
            points = task.points
            
            # إضافة النقاط إلى المستخدم
            user.add_points(points)
            
            # زيادة عدد المهام المكتملة
            user.increment_tasks_completed()
            
            # حفظ التغييرات
            db.session.commit()
            
            answer_callback_query(callback_query_id, f"✅ تم تسجيل انضمامك للمهمة! +{points} نقطة", True)
            logger.info(f"تم تسجيل انضمام المستخدم {user_id} للمهمة {task_type}")
            return True
        else:
            answer_callback_query(callback_query_id, "❌ حدث خطأ أثناء تسجيل انضمامك للمهمة.", True)
            return False
    except Exception as e:
        logger.error(f"خطأ في معالجة طلب الانضمام للمهمة {task_type}: {e}")
        answer_callback_query(callback_query_id, "❌ حدث خطأ أثناء معالجة طلبك.", True)
        return False


# الحصول على الاسم العربي للمهمة
def get_task_name(task_type):
    """الحصول على الاسم العربي للمهمة"""
    task_names = {
        "daily_plan": "خطة اليوم الدراسي",
        "prayer_1": "صلاة الفجر",
        "breakfast": "الفطور والراحة",
        "back_to_study": "العودة للمذاكرة",
        "short_break": "استراحة قصيرة",
        "back_after_break": "العودة بعد الراحة",
        "prayer_2": "صلاة الظهر",
        "after_prayer_study": "المذاكرة بعد الصلاة",
        "nap_time": "وقت القيلولة",
        "wake_up": "الاستيقاظ",
        "prayer_3": "صلاة العصر",
        "study_3": "المذاكرة المسائية",
        "prayer_4": "صلاة المغرب",
        "prayer_5": "صلاة العشاء",
        "evaluation": "تقييم اليوم",
        "evening_plan": "الهدف الليلي الدراسي",
        "evening_study": "وقت الإنجاز الحقيقي",
        "dinner_break": "استراحة العشاء",
        "night_study": "العودة للمذاكرة",
        "qiyam": "قيام الليل",
        "long_break": "استراحة طويلة",
        "night_evaluation": "تقييم الليل"
    }
    
    return task_names.get(task_type, "مهمة غير معروفة")


# إرسال مهمة بناءً على نوعها ونوع الجدول
def send_task_by_type(group_id, task_type, schedule_type='morning'):
    """إرسال مهمة بناءً على نوعها ونوع الجدول"""
    try:
        # الحصول على المجموعة
        group = Group.query.get(group_id)
        if not group:
            logger.error(f"لم يتم العثور على المجموعة {group_id}")
            return False
            
        # البحث عن المهمة في الجدول المناسب
        schedule = MORNING_SCHEDULE if schedule_type == 'morning' else EVENING_SCHEDULE
        task_item = None
        
        for item in schedule:
            if item[1] == task_type:
                task_item = item
                break
                
        if not task_item:
            logger.error(f"لم يتم العثور على المهمة {task_type} في الجدول {schedule_type}")
            return False
            
        # استخراج بيانات المهمة
        _, task_type, text, points = task_item
        
        # إرسال رسالة المهمة
        result = send_group_task_message(group_id, task_type, text, points, deadline_minutes=15)
        return result is not None
    except Exception as e:
        logger.error(f"خطأ في إرسال المهمة {task_type} للمجموعة {group_id}: {e}")
        return False


# إرسال مهمة بناءً على وقت محدد وجدول المجموعة
def send_scheduled_task(group_id, time_str, schedule_type='morning'):
    """إرسال مهمة بناءً على وقت محدد وجدول المجموعة"""
    try:
        # الحصول على المجموعة
        group = Group.query.get(group_id)
        if not group:
            logger.error(f"لم يتم العثور على المجموعة {group_id}")
            return False
            
        # البحث عن المهمة في الجدول المناسب بناءً على الوقت
        schedule = MORNING_SCHEDULE if schedule_type == 'morning' else EVENING_SCHEDULE
        tasks_for_time = [item for item in schedule if item[0] == time_str]
        
        if not tasks_for_time:
            logger.info(f"لا توجد مهام مجدولة للوقت {time_str} في الجدول {schedule_type}")
            return False
            
        # إرسال المهام المجدولة للوقت المحدد
        sent_count = 0
        for task_item in tasks_for_time:
            time_str, task_type, text, points = task_item
            result = send_group_task_message(group_id, task_type, text, points, deadline_minutes=15)
            if result:
                sent_count += 1
                
        logger.info(f"تم إرسال {sent_count} مهمة للمجموعة {group_id} في الوقت {time_str}")
        return sent_count > 0
    except Exception as e:
        logger.error(f"خطأ في إرسال المهام المجدولة للوقت {time_str} للمجموعة {group_id}: {e}")
        return False


# إرسال مهام الجدول الصباحي للمجموعات النشطة
def send_morning_schedule_tasks():
    """إرسال مهام الجدول الصباحي للمجموعات النشطة"""
    try:
        # الحصول على الوقت الحالي
        now = get_current_time()
        time_str = now.strftime("%H:%M")
        
        # تسجيل وقت الفحص
        logger.info(f"فحص مهام الجدول الصباحي للوقت {time_str}")
        
        # الحصول على المجموعات النشطة مع تفعيل الجدول الصباحي
        active_groups = Group.query.filter_by(is_active=True, morning_schedule_enabled=True).all()
        logger.info(f"تم العثور على {len(active_groups)} مجموعة نشطة مع تفعيل الجدول الصباحي")
        
        # إرسال المهام المجدولة للوقت الحالي
        sent_count = 0
        for group in active_groups:
            result = send_scheduled_task(group.id, time_str, 'morning')
            if result:
                sent_count += 1
                
        logger.info(f"تم إرسال {sent_count} مهمة صباحية للوقت {time_str}")
        return sent_count
    except Exception as e:
        logger.error(f"خطأ في إرسال مهام الجدول الصباحي: {e}")
        return 0


# إرسال مهام الجدول المسائي للمجموعات النشطة
def send_evening_schedule_tasks():
    """إرسال مهام الجدول المسائي للمجموعات النشطة"""
    try:
        # الحصول على الوقت الحالي
        now = get_current_time()
        time_str = now.strftime("%H:%M")
        
        # تسجيل وقت الفحص
        logger.info(f"فحص مهام الجدول المسائي للوقت {time_str}")
        
        # الحصول على المجموعات النشطة مع تفعيل الجدول المسائي
        active_groups = Group.query.filter_by(is_active=True, evening_schedule_enabled=True).all()
        logger.info(f"تم العثور على {len(active_groups)} مجموعة نشطة مع تفعيل الجدول المسائي")
        
        # إرسال المهام المجدولة للوقت الحالي
        sent_count = 0
        for group in active_groups:
            result = send_scheduled_task(group.id, time_str, 'evening')
            if result:
                sent_count += 1
                
        logger.info(f"تم إرسال {sent_count} مهمة مسائية للوقت {time_str}")
        return sent_count
    except Exception as e:
        logger.error(f"خطأ في إرسال مهام الجدول المسائي: {e}")
        return 0


# فحص وإرسال مهام المجموعات المجدولة
def check_group_schedule_tasks():
    """فحص وإرسال مهام المجموعات المجدولة"""
    try:
        # تسجيل بدء الفحص
        logger.info("بدء فحص مهام المجموعات المجدولة")
        
        # إرسال مهام الجدول الصباحي
        morning_count = send_morning_schedule_tasks()
        
        # إرسال مهام الجدول المسائي
        evening_count = send_evening_schedule_tasks()
        
        # تسجيل نتائج الفحص
        logger.info(f"تم إرسال {morning_count} مهمة صباحية و {evening_count} مهمة مسائية")
        
        return morning_count + evening_count
    except Exception as e:
        logger.error(f"خطأ في فحص مهام المجموعات المجدولة: {e}")
        return 0