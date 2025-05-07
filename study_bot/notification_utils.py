"""
وحدة وظائف الإشعارات
تحتوي على وظائف الإشعارات المشتركة بين مختلف وحدات البوت
"""

import json
import random
import uuid
import threading
import time
import traceback
from threading import Timer
from datetime import datetime, timedelta

from study_bot.config import logger, TELEGRAM_API_URL

# قاموس لتخزين المؤقتات
_activation_timers = {}
_timers_lock = threading.Lock()

def schedule_confirmation_message(chat_id, is_group=False, user_id=None, delay_seconds=120):
    """
    جدولة رسالة تأكيد بعد فترة زمنية محددة (الافتراضي: دقيقتان)
    """
    try:
        # إنشاء معرف فريد للمؤقت
        timer_id = str(uuid.uuid4())
        
        def send_confirmation_message():
            try:
                # استيراد الوظائف هنا لتجنب الاستيرادات الدائرية
                from study_bot.group_tasks import MOTIVATIONAL_QUOTES
                from study_bot.bot import send_message
                
                # إختيار رسالة تحفيزية عشوائية
                quote = random.choice(MOTIVATIONAL_QUOTES)
                
                # إضافة نص التأكيد
                confirmation_message = f"✅ <b>تأكيد التفعيل</b>\n\nتم تفعيل بوت الدراسة والتحفيز بنجاح.\n\n{quote}\n\n<i>فريق المطورين - @M_o_h_a_m_e_d_501</i>"
                
                # إرسال الرسالة
                send_message(chat_id, confirmation_message)
                
                logger.info(f"تم إرسال رسالة تأكيد التفعيل إلى {chat_id}")
                
                # إذا كانت المجموعة، أرسل رسالة للمشرف في الخاص
                if is_group and user_id:
                    send_admin_private_message(chat_id, user_id)
                
                # إزالة المؤقت من القاموس
                with _timers_lock:
                    if timer_id in _activation_timers:
                        del _activation_timers[timer_id]
            except Exception as e:
                logger.error(f"خطأ في إرسال رسالة تأكيد التفعيل: {e}")
                logger.error(traceback.format_exc())
        
        # إنشاء مؤقت لإرسال الرسالة بعد المدة المحددة
        timer = Timer(delay_seconds, send_confirmation_message)
        timer.daemon = True  # جعل المؤقت خلفي لإيقافه عند إيقاف التطبيق
        timer.start()
        
        # تخزين المؤقت للرجوع إليه لاحقاً
        with _timers_lock:
            _activation_timers[timer_id] = timer
        
        logger.info(f"تم جدولة رسالة تأكيد التفعيل لـ {chat_id} بعد {delay_seconds} ثانية")
        return timer_id
    except Exception as e:
        logger.error(f"خطأ في جدولة رسالة تأكيد التفعيل: {e}")
        logger.error(traceback.format_exc())
        return None


def send_admin_private_message(group_id, admin_id):
    """
    إرسال رسالة للمشرف في الخاص بعد تفعيل البوت في مجموعة
    """
    try:
        # استيراد النماذج والوظائف هنا لتجنب الاستيرادات الدائرية
        from study_bot.models import Group, User
        from study_bot.bot import send_message
        
        # الحصول على معلومات المجموعة
        group = Group.query.filter_by(telegram_id=group_id).first()
        if not group:
            # محاولة جلب المجموعة بالمعرف الرقمي
            group = Group.query.filter_by(id=group_id).first()
            if not group:
                logger.error(f"لم يتم العثور على المجموعة بالمعرف {group_id}")
                return False
        
        # التحقق من وجود المستخدم
        user = User.query.filter_by(telegram_id=admin_id).first()
        if not user:
            # إنشاء مستخدم جديد إذا لم يكن موجودًا
            user = User(
                telegram_id=admin_id,
                is_active=True
            )
            from study_bot.models import db
            db.session.add(user)
            db.session.commit()
        
        # إرسال رسالة للمشرف
        admin_message = f"""👋 <b>مرحباً بك في بوت الدراسة والتحفيز!</b>

تم تفعيل البوت بنجاح في مجموعة "{group.title}".

بصفتك مشرف المجموعة، يمكنك إدارة إعدادات البوت من هنا:
• تفعيل جداول دراسية (صباحية أو مسائية)
• إنشاء معسكرات دراسية مخصصة
• إدارة الرسائل التحفيزية
• مراقبة أداء المجموعة

استخدم الأمر /groups لعرض المجموعات التي تديرها.
استخدم الأمر /camps لإدارة المعسكرات الدراسية.

تفضل بزيارة موقعنا للمزيد من المعلومات والمساعدة.
"""
        
        result = send_message(admin_id, admin_message)
        
        if result:
            logger.info(f"تم إرسال رسالة للمشرف {admin_id} بنجاح")
            return True
        else:
            logger.error(f"فشل إرسال رسالة للمشرف {admin_id}")
            return False
    except Exception as e:
        logger.error(f"خطأ في إرسال رسالة للمشرف في الخاص: {e}")
        logger.error(traceback.format_exc())
        return False


def schedule_task_reminder(user_id, task_name, task_type, time_minutes, ignore_preferences=False):
    """
    جدولة رسالة تذكير بمهمة بعد فترة زمنية محددة بالدقائق
    """
    try:
        # استيراد النماذج هنا لتجنب الاستيرادات الدائرية
        from study_bot.models import User, NotificationPreference
        
        # التحقق من تفضيلات الإشعارات للمستخدم
        user = User.query.filter_by(telegram_id=user_id).first()
        if not user:
            logger.warning(f"المستخدم {user_id} غير موجود")
            return None
        
        # التحقق من الإشعارات الذكية إذا لم يتم تجاهل التفضيلات
        if not ignore_preferences and not user.smart_notifications_enabled:
            logger.info(f"الإشعارات الذكية معطلة للمستخدم {user_id}")
            return None
        
        # إنشاء معرف فريد للمؤقت
        timer_id = str(uuid.uuid4())
        
        def send_reminder_message():
            try:
                # استيراد الوظائف هنا لتجنب الاستيرادات الدائرية
                from study_bot.bot import send_message
                
                # إعداد نص التذكير حسب نوع المهمة
                reminder_message = get_reminder_text(task_name, task_type)
                
                # إرسال التذكير
                send_message(user_id, reminder_message)
                
                logger.info(f"تم إرسال تذكير بمهمة {task_name} للمستخدم {user_id}")
                
                # إزالة المؤقت من القاموس
                with _timers_lock:
                    if timer_id in _activation_timers:
                        del _activation_timers[timer_id]
            except Exception as e:
                logger.error(f"خطأ في إرسال تذكير بمهمة: {e}")
                logger.error(traceback.format_exc())
        
        # إنشاء مؤقت لإرسال التذكير بعد المدة المحددة
        timer = Timer(time_minutes * 60, send_reminder_message)
        timer.daemon = True  # جعل المؤقت خلفي لإيقافه عند إيقاف التطبيق
        timer.start()
        
        # تخزين المؤقت للرجوع إليه لاحقاً
        with _timers_lock:
            _activation_timers[timer_id] = timer
        
        logger.info(f"تم جدولة تذكير بمهمة {task_name} للمستخدم {user_id} بعد {time_minutes} دقيقة")
        return timer_id
    except Exception as e:
        logger.error(f"خطأ في جدولة تذكير بمهمة: {e}")
        logger.error(traceback.format_exc())
        return None


def get_reminder_text(task_name, task_type):
    """الحصول على نص التذكير حسب نوع المهمة"""
    # رسائل تذكير للجدول الصباحي
    morning_reminders = {
        "prayer_1": "🕋 <b>تذكير: صلاة الفجر</b>\n\nلقد حان وقت صلاة الفجر. لا تنسَ أداء الصلاة في وقتها.",
        "meal_1": "☕ <b>تذكير: وقت الإفطار</b>\n\nمن المهم تناول وجبة إفطار صحية ومتوازنة لبدء يومك بنشاط.",
        "study_1": "📚 <b>تذكير: بدء المذاكرة</b>\n\nحان وقت البدء في المذاكرة. خصص الوقت الكافي للتركيز.",
        "prayer_2": "🕌 <b>تذكير: صلاة الظهر</b>\n\nلقد حان وقت صلاة الظهر. خذ استراحة لأداء الصلاة.",
        "study_2": "✏️ <b>تذكير: المذاكرة بعد الظهر</b>\n\nاستأنف المذاكرة بعد الظهر بنشاط وتركيز.",
        "prayer_3": "🕌 <b>تذكير: صلاة العصر</b>\n\nلقد حان وقت صلاة العصر. لا تنسَ أداء الصلاة في وقتها.",
        "study_3": "📖 <b>تذكير: المراجعة</b>\n\nخصص وقتًا للمراجعة وتثبيت المعلومات.",
        "prayer_4": "🕌 <b>تذكير: صلاة المغرب</b>\n\nلقد حان وقت صلاة المغرب. خذ استراحة لأداء الصلاة.",
        "prayer_5": "🕌 <b>تذكير: صلاة العشاء</b>\n\nلقد حان وقت صلاة العشاء. لا تنسَ أداء الصلاة في وقتها.",
        "evaluation": "✍️ <b>تذكير: تقييم اليوم</b>\n\nحان وقت تقييم إنجازات اليوم والتخطيط لليوم التالي."
    }
    
    # رسائل تذكير للجدول المسائي
    evening_reminders = {
        "join": "🌙 <b>تذكير: بدء المعسكر المسائي</b>\n\nحان وقت البدء في معسكر الدراسة المسائي.",
        "study_1": "📚 <b>تذكير: وقت المراجعة</b>\n\nحان وقت مراجعة ما سبق دراسته. ركز على النقاط المهمة.",
        "prayer_1": "🕌 <b>تذكير: صلاة المغرب</b>\n\nلقد حان وقت صلاة المغرب. خذ استراحة لأداء الصلاة.",
        "study_2": "✏️ <b>تذكير: الواجبات والتدريبات</b>\n\nحان وقت العمل على الواجبات وحل التدريبات.",
        "prayer_2": "🕌 <b>تذكير: صلاة العشاء</b>\n\nلقد حان وقت صلاة العشاء. لا تنسَ أداء الصلاة في وقتها.",
        "study_3": "📖 <b>تذكير: القراءة والحفظ</b>\n\nخصص وقتًا للقراءة أو الحفظ لترسيخ المعلومات.",
        "evaluation": "✍️ <b>تذكير: تقييم اليوم</b>\n\nحان وقت تقييم إنجازات اليوم والتخطيط لليوم التالي.",
        "early_sleep": "💤 <b>تذكير: النوم المبكر</b>\n\nحان وقت الاستعداد للنوم مبكرًا للاستيقاظ نشيطًا غدًا."
    }
    
    # تحديد مجموعة التذكيرات المناسبة حسب نوع الجدول
    if task_type == 'morning':
        reminders = morning_reminders
    elif task_type == 'evening':
        reminders = evening_reminders
    else:
        # تذكير افتراضي للمعسكرات المخصصة
        return f"⏰ <b>تذكير: {task_name}</b>\n\nحان وقت إكمال هذه المهمة في جدولك الدراسي."
    
    # إرجاع التذكير المناسب أو تذكير افتراضي
    return reminders.get(task_name, f"⏰ <b>تذكير: {task_name}</b>\n\nلديك مهمة في جدولك الدراسي.")


def cancel_all_timers():
    """إلغاء جميع المؤقتات النشطة"""
    try:
        with _timers_lock:
            for timer_id, timer in list(_activation_timers.items()):
                timer.cancel()
                del _activation_timers[timer_id]
        
        logger.info(f"تم إلغاء {len(_activation_timers)} مؤقت نشط")
        return True
    except Exception as e:
        logger.error(f"خطأ في إلغاء المؤقتات النشطة: {e}")
        logger.error(traceback.format_exc())
        return False