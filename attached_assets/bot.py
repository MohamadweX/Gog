#!/usr/bin/env python3
"""
وحدة البوت الرئيسية
تحتوي على وظائف للتفاعل مع واجهة برمجة تطبيقات تيليجرام
"""

import os
import sys
import json
import requests
import threading
import traceback
from datetime import datetime, timedelta
from flask import Flask

# استيراد الإعدادات
from study_bot.config import TELEGRAM_BOT_TOKEN, TELEGRAM_API_URL, logger
from study_bot.models import User, Group, UserActivity, ScheduleTracker, MotivationalMessage, SystemStat, UserSchedule, NotificationPreference, db
from study_bot.camps_models import CustomCamp, CampTask, CampParticipant, CampTaskParticipation
from study_bot.utils import get_morning_schedule_text, get_evening_schedule_text, get_custom_schedule_text

# كائن البوت العمومي للاستخدام في وظائف أخرى
_bot = None

# تعريف القائمة الرئيسية
MAIN_MENU = {
    'inline_keyboard': [
        [{'text': '🗓️ جدولي', 'callback_data': 'my_schedule'}],
        [{'text': '🏆 نقاطي', 'callback_data': 'my_points'}],
        [{'text': '✨ رسالة تحفيزية', 'callback_data': 'motivational_message'}],
        [{'text': '⚙️ الإعدادات', 'callback_data': 'settings'}],
        [{'text': '❓ المساعدة', 'callback_data': 'help'}]
    ]
}

# تعريف قائمة الإعدادات
SETTINGS_MENU = {
    'inline_keyboard': [
        [{'text': '👥 إدارة المجموعات', 'callback_data': 'groups_setup'}],
        [{'text': '🏝️ إدارة المعسكرات الدراسية', 'callback_data': 'camps_setup'}],
        [{'text': '📅 تغيير نوع الجدول', 'callback_data': 'change_schedule_type'}],
        [{'text': '🔔 إعدادات الإشعارات', 'callback_data': 'notification_settings'}],
        [{'text': '✨ تفعيل/إيقاف الرسائل التحفيزية', 'callback_data': 'toggle_motivation'}],
        [{'text': '🔙 رجوع', 'callback_data': 'back_to_main'}]
    ]
}

# تعريف قائمة اختيار نوع الجدول
SCHEDULE_TYPE_MENU = {
    'inline_keyboard': [
        [{'text': '🌞 الجدول الصباحي', 'callback_data': 'schedule_morning'}],
        [{'text': '🌙 الجدول المسائي', 'callback_data': 'schedule_evening'}],
        [{'text': '🏕️ معسكر مخصص', 'callback_data': 'schedule_custom'}],
        [{'text': '❌ إلغاء الجدول', 'callback_data': 'schedule_none'}],
        [{'text': '🔙 رجوع', 'callback_data': 'back_to_settings'}]
    ]
}

# تعريف قائمة إعدادات الإشعارات
NOTIFICATION_SETTINGS_MENU = {
    'inline_keyboard': [
        [{'text': '🔄 تشغيل/إيقاف محسن الإشعارات الذكي', 'callback_data': 'toggle_smart_notifications'}],
        [{'text': '🕓 ضبط حساسية التوقيت', 'callback_data': 'set_notification_sensitivity'}],
        [{'text': '🔢 ضبط عدد الإشعارات اليومية', 'callback_data': 'set_max_notifications'}],
        [{'text': '🔙 رجوع', 'callback_data': 'back_to_settings'}]
    ]
}

def send_message(chat_id, text, reply_markup=None, parse_mode='HTML'):
    """إرسال رسالة إلى مستخدم أو مجموعة"""
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': parse_mode
    }
    
    if reply_markup:
        payload['reply_markup'] = json.dumps(reply_markup)
    
    try:
        response = requests.post(url, json=payload)
        result = response.json()
        
        if response.status_code == 200 and result.get('ok'):
            # زيادة عدد الرسائل المرسلة في الإحصائيات
            SystemStat.increment('messages_sent')
            return result['result']
        else:
            logger.error(f"خطأ في إرسال الرسالة: {result}")
            return None
    except Exception as e:
        logger.error(f"استثناء عند إرسال الرسالة: {e}")
        return None

def show_main_menu(chat_id):
    """عرض القائمة الرئيسية للمستخدم"""
    main_menu_message = """💻 <b>القائمة الرئيسية</b>
    
اختر من القائمة أدناه:
"""
    send_message(chat_id, main_menu_message, MAIN_MENU)
    return True

def handle_start_command(user_data):
    """معالجة أمر /start"""
    chat_id = user_data['chat_id']
    user_id = user_data['user_id']
    
    # التحقق من وجود معاملات
    command_args = user_data.get('text', '').split(maxsplit=1)
    if len(command_args) > 1 and command_args[1] == 'setup_group':
        # المستخدم قادم من مجموعة لإعداد البوت
        return handle_private_group_setup(user_id, chat_id)
    
    # كود البدء العادي
    user = User.query.filter_by(telegram_id=user_id).first()
    
    if not user:
        # مستخدم جديد
        user = User.get_or_create(telegram_id=user_id)
        logger.info(f"تم إنشاء مستخدم جديد: {user_id}")
        
        # رسالة الترحيب
        welcome_message = f"""
مرحبًا بك في بوت جدولة الدراسة والتحفيز! 👋

يمكنك استخدام هذا البوت لمساعدتك في تنظيم جدولك الدراسي، وتلقي تذكيرات بالمهام والصلوات، والحصول على رسائل تحفيزية.

الأوامر المتاحة:
/schedule - عرض وتغيير نوع الجدول
/points - عرض نقاطك الحالية
/motivation - الحصول على رسالة تحفيزية
/settings - تغيير إعدادات البوت
/help - عرض هذه الرسالة

تم تصميم البوت لمساعدتك في الحفاظ على التوازن بين الدراسة والعبادة والراحة.

للبدء، اختر نوع الجدول الذي يناسبك باستخدام الأمر /schedule
"""
        
        # إرسال رسالة الترحيب
        send_message(chat_id, welcome_message)
    else:
        # مستخدم موجود
        welcome_back_message = f"""
أهلاً بعودتك! 👋

ماذا تريد أن تفعل اليوم؟

/schedule - عرض وتغيير نوع الجدول
/points - عرض نقاطك الحالية
/motivation - الحصول على رسالة تحفيزية
/settings - تغيير إعدادات البوت
/today - عرض جدول اليوم
/report - عرض تقرير أدائك

جدولك الحالي: {user.preferred_schedule if user.preferred_schedule != 'none' else 'غير محدد ❔'}
نقاطك الإجمالية: {user.total_points} 🏆
"""
        
        send_message(chat_id, welcome_back_message)
    
    return True

def handle_private_group_setup(user_id, chat_id):
    """معالجة إعدادات المجموعة في الخاص"""
    # استخدام مدير المعسكرات الخاصة
    from study_bot.private_camp_manager import handle_private_group_setup as camp_manager_group_setup
    return camp_manager_group_setup(user_id, chat_id)



def handle_help_command(user_data):
    """معالجة أمر /help"""
    chat_id = user_data['chat_id']
    
    help_message = """
<b>📚 الأوامر المتاحة:</b>

/start - بدء استخدام البوت
/help - عرض هذه المساعدة
/developer - معلومات عن مطور البوت
/schedule - عرض جدولك الحالي
/points - عرض نقاطك ومستواك
/motivation - الحصول على رسالة تحفيزية
/settings - تغيير إعدادات البوت
/done [task] - تسجيل إكمال مهمة (مثال: /done prayer_1)
/today - إظهار مهام اليوم
/report - عرض تقرير أدائك الأسبوعي

<b>🔍 نبذة عن الجداول:</b>
• <b>الجدول الصباحي</b>: يبدأ مع صلاة الفجر وينتهي بعد صلاة العشاء
• <b>الجدول المسائي</b>: يبدأ من بعد الظهر وحتى وقت النوم
• <b>المعسكر المخصص</b>: يمكنك إنشاء معسكر دراسي خاص بك

<b>💡 نصائح:</b>
• سجل إكمال المهام باستخدام أزرار الجدول أو الأمر /done
• اطلب تذكيراً بمهامك اليومية باستخدام /today
• حافظ على التزامك اليومي لكسب المزيد من النقاط
"""
    
    # إرسال الرسالة مع القائمة الرئيسية
    send_message(chat_id, help_message, MAIN_MENU)
    
    return True

def handle_group_help_command(user_data):
    """معالجة أمر /grouphelp"""
    chat_id = user_data['chat_id']
    
    group_help_message = """
<b>🛠️ مساعدة إدارة المجموعات والمعسكرات الدراسية</b>

<b>أولاً: أوامر إدارة المجموعات:</b>

/start - تفعيل البوت في المجموعة
/group_settings - تغيير إعدادات المجموعة
/group_schedule - اختيار نوع جدول المجموعة
/group_report - عرض تقرير أداء المجموعة
/group_leaderboard - عرض قائمة المتصدرين في المجموعة

<b>ثانياً: أوامر المعسكرات الدراسية:</b>

/newcamp - إنشاء معسكر دراسي جديد
/campdetails - عرض تفاصيل المعسكر الحالي
/campstats - عرض إحصائيات المعسكر والمشاركين
/camptasks - عرض وإدارة مهام المعسكر

<b>ثالثاً: كيفية إنشاء معسكر دراسي جديد:</b>

١. استخدم الأمر /newcamp في المجموعة
٢. سيتم إرسال رسالة للمشرف في الخاص لإعداد المعسكر
٣. حدد اسم المعسكر ووصفه وفترته
٤. أضف المهام والأنشطة المطلوبة
٥. اضبط نظام النقاط والتحفيز

<b>رابعاً: مميزات المعسكرات الدراسية:</b>

• إمكانية تخصيص كاملة للمهام والأوقات
• نظام تذكير آلي بمواعيد المهام
• نظام نقاط تحفيزي للمشاركين
• إحصائيات وتقارير دورية للمشاركين
• لوحة متصدرين لتشجيع المنافسة الإيجابية

<i>للحصول على مزيد من المساعدة، تواصل مع مطور البوت: @M_o_h_a_m_e_d_501</i>
"""
    
    # إرسال الرسالة مع زر الرجوع للقائمة الرئيسية
    back_button = {
        'inline_keyboard': [
            [{'text': '🔙 رجوع للقائمة الرئيسية', 'callback_data': 'back_to_main'}]
        ]
    }
    
    send_message(chat_id, group_help_message, back_button)
    
    return True

def handle_schedule_command(user_data):
    """معالجة أمر /schedule"""
    chat_id = user_data['chat_id']
    user_id = user_data['user_id']
    
    # الحصول على المستخدم من قاعدة البيانات
    user = User.query.filter_by(telegram_id=user_id).first()
    
    if not user:
        send_message(chat_id, "❗ حدث خطأ في العثور على بياناتك. يرجى إرسال /start للبدء من جديد.")
        return False
    
    # التحقق من نوع الجدول المفضل للمستخدم
    schedule_type = user.preferred_schedule
    
    if schedule_type == 'none':
        # المستخدم ليس لديه جدول مفضل
        no_schedule_message = """
❗ ليس لديك جدول مفعّل حالياً.

لتفعيل جدول جديد، اختر من القائمة أدناه:
"""
        send_message(chat_id, no_schedule_message, SCHEDULE_TYPE_MENU)
        return True
    
    # الحصول على متابعة الجدول ليوم اليوم
    tracker = ScheduleTracker.get_or_create_for_today(user.id, schedule_type)
    
    # عرض الجدول المناسب
    if schedule_type == 'morning':
        schedule_text = get_morning_schedule_text(tracker)
    elif schedule_type == 'evening':
        schedule_text = get_evening_schedule_text(tracker)
    elif schedule_type == 'custom':
        # الحصول على المعسكر المخصص
        user_schedule = UserSchedule.query.filter_by(user_id=user.id, schedule_type='custom').first()
        if user_schedule and user_schedule.custom_schedule:
            schedule_text = get_custom_schedule_text(tracker, user_schedule.custom_schedule)
        else:
            schedule_text = "❗ لم يتم العثور على معسكر مخصص. يرجى تهيئة معسكرك المخصص أولاً."
    
    # إنشاء أزرار لتسجيل اكتمال المهام
    task_buttons = create_task_buttons(tracker, schedule_type)
    
    # إرسال الجدول
    send_message(chat_id, schedule_text, task_buttons)
    
    return True

def create_task_buttons(tracker, schedule_type):
    """إنشاء أزرار لتسجيل اكتمال المهام حسب نوع الجدول"""
    buttons = {'inline_keyboard': []}
    
    # المهام المشتركة
    common_tasks = [
        ('joined', '✅ تسجيل حضور'),
        ('prayer_1', '🕌 صلاة الفجر' if schedule_type == 'morning' else '🕌 صلاة المغرب'),
        ('study_1', '📚 المذاكرة الأولى')
    ]
    
    # تعريف قائمة المهام
    tasks = []
    
    # إضافة المهام حسب نوع الجدول
    if schedule_type == 'morning':
        tasks = common_tasks + [
            ('meal_1', '🍳 الإفطار'),
            ('prayer_2', '🕌 صلاة الظهر'),
            ('study_2', '📚 المذاكرة الثانية'),
            ('return_after_break', '🔄 العودة بعد الراحة'),
            ('prayer_3', '🕌 صلاة العصر'),
            ('study_3', '📚 المراجعة'),
            ('prayer_4', '🕌 صلاة المغرب'),
            ('prayer_5', '🕌 صلاة العشاء'),
            ('evaluation', '📝 تقييم اليوم')
        ]
    elif schedule_type == 'evening':
        tasks = common_tasks + [
            ('prayer_2', '🕌 صلاة العشاء'),
            ('study_2', '📚 المذاكرة الثانية'),
            ('study_3', '📚 الحفظ/القراءة'),
            ('evaluation', '📝 تقييم اليوم'),
            ('early_sleep', '💤 النوم المبكر')
        ]
    # للجداول المخصصة أو أي جدول آخر
    else:
        tasks = common_tasks + [
            ('evaluation', '📝 تقييم اليوم')
        ]
    
    # إنشاء الأزرار لكل مهمة
    for task_name, task_label in tasks:
        task_status = getattr(tracker, task_name, False)
        
        # إذا كانت المهمة مكتملة، أضف علامة ✓
        if task_status:
            button_text = f"✓ {task_label}"
        else:
            button_text = task_label
        
        # إضافة زر للمهمة
        button = {'text': button_text, 'callback_data': f"complete_{task_name}"}
        buttons['inline_keyboard'].append([button])
    
    # إضافة زر للعودة إلى القائمة الرئيسية
    buttons['inline_keyboard'].append([{'text': '🔙 رجوع للقائمة الرئيسية', 'callback_data': 'back_to_main'}])
    
    return buttons

def show_main_menu(chat_id):
    """عرض القائمة الرئيسية للمستخدم"""
    try:
        # إرسال رسالة القائمة الرئيسية
        welcome_message = """👋 <b>مرحباً بك في بوت الدراسة والتحفيز</b>

اختر من القائمة أدناه:"""
        send_message(chat_id, welcome_message, MAIN_MENU)
        return True
    except Exception as e:
        logger.error(f"خطأ في عرض القائمة الرئيسية: {e}")
        return False


def handle_points_command(user_data):
    """معالجة أمر /points"""
    chat_id = user_data['chat_id']
    user_id = user_data['user_id']
    
    # الحصول على المستخدم من قاعدة البيانات
    user = User.query.filter_by(telegram_id=user_id).first()
    
    if not user:
        send_message(chat_id, "❗ حدث خطأ في العثور على بياناتك. يرجى إرسال /start للبدء من جديد.")
        return False
    
    # حساب مستوى المستخدم (كل 100 نقطة ترفع المستوى)
    level = (user.total_points // 100) + 1
    progress_to_next = user.total_points % 100
    progress_bar = generate_progress_bar(progress_to_next, 100, 10)
    
    # جمع إحصائيات الإنجازات
    completed_days = ScheduleTracker.query.filter_by(user_id=user.id, completed=True).count()
    
    points_message = f"""
<b>🏆 نقاطك وإنجازاتك:</b>

<b>المستوى:</b> {level} 🌟
<b>إجمالي النقاط:</b> {user.total_points} نقطة
<b>نقاط الجدول الصباحي:</b> {user.morning_points} نقطة
<b>نقاط الجدول المسائي:</b> {user.evening_points} نقطة

<b>التقدم للمستوى التالي:</b>
{progress_bar} {progress_to_next}/100

<b>إنجازاتك:</b>
• أيام مكتملة: {completed_days} يوم
• متوسط النقاط اليومية: {calculate_avg_daily_points(user)} نقطة

<b>💪 استمر في العمل الجيد!</b>
كل التزام يومي يقربك من أهدافك ويرفع مستواك.
"""
    
    # إرسال رسالة النقاط
    send_message(chat_id, points_message, MAIN_MENU)
    
    return True

def calculate_avg_daily_points(user):
    """حساب متوسط النقاط اليومية للمستخدم"""
    # الحصول على تاريخ بدء استخدام البوت للمستخدم
    start_date = user.registration_date.date()
    
    # حساب عدد الأيام منذ بدء الاستخدام (على الأقل يوم واحد)
    days_since_start = max(1, (datetime.utcnow().date() - start_date).days)
    
    # حساب المتوسط
    avg_points = user.total_points / days_since_start
    
    return round(avg_points, 1)

def generate_progress_bar(current, total, length=10):
    """إنشاء شريط تقدم نصي"""
    progress = min(1, current / total)
    filled_length = int(length * progress)
    
    bar = '█' * filled_length + '░' * (length - filled_length)
    
    return bar

def handle_motivation_command(user_data):
    """معالجة أمر /motivation"""
    chat_id = user_data['chat_id']
    user_id = user_data['user_id']
    
    # الحصول على المستخدم من قاعدة البيانات
    user = User.query.filter_by(telegram_id=user_id).first()
    
    if not user:
        send_message(chat_id, "❗ حدث خطأ في العثور على بياناتك. يرجى إرسال /start للبدء من جديد.")
        return False
    
    # الحصول على رسالة تحفيزية عشوائية
    # يمكن تخصيص نوع الرسالة حسب وقت اليوم أو جدول المستخدم
    if user.preferred_schedule == 'morning':
        message = MotivationalMessage.get_random_message('morning')
    elif user.preferred_schedule == 'evening':
        message = MotivationalMessage.get_random_message('evening')
    else:
        message = MotivationalMessage.get_random_message('general')
    
    # إرسال الرسالة التحفيزية
    motivation_text = f"""
<b>✨ رسالة تحفيزية لك:</b>

"{message}"

<b>استمر في رحلتك نحو النجاح! 🚀</b>
"""
    
    send_message(chat_id, motivation_text, MAIN_MENU)
    
    return True

def handle_settings_command(user_data):
    """معالجة أمر /settings"""
    chat_id = user_data['chat_id']
    
    settings_message = """
<b>⚙️ إعدادات البوت:</b>

اختر أحد الخيارات أدناه لتعديل الإعدادات:
"""
    
    send_message(chat_id, settings_message, SETTINGS_MENU)
    
    return True

def handle_done_command(user_data, command_args):
    """معالجة أمر /done لتسجيل إكمال مهمة"""
    chat_id = user_data['chat_id']
    user_id = user_data['user_id']
    
    # الحصول على المستخدم من قاعدة البيانات
    user = User.query.filter_by(telegram_id=user_id).first()
    
    if not user:
        send_message(chat_id, "❗ حدث خطأ في العثور على بياناتك. يرجى إرسال /start للبدء من جديد.")
        return False
    
    # التحقق من وجود اسم المهمة
    if not command_args:
        tasks_message = """
❗ يرجى تحديد اسم المهمة.

<b>مثال:</b> <code>/done prayer_1</code>

<b>المهام المتاحة:</b>
- prayer_1, prayer_2, ...
- study_1, study_2, ...
- meal_1
- evaluation
- وغيرها...

استخدم أمر /schedule لرؤية جدولك ومهامك.
"""
        send_message(chat_id, tasks_message)
        return False
    
    task_name = command_args[0]
    
    # التحقق من نوع الجدول المفضل للمستخدم
    schedule_type = user.preferred_schedule
    
    if schedule_type == 'none':
        send_message(chat_id, "❗ ليس لديك جدول مفعّل حالياً. استخدم /settings لإعداد جدول.")
        return False
    
    # الحصول على متابعة الجدول ليوم اليوم
    tracker = ScheduleTracker.get_or_create_for_today(user.id, schedule_type)
    
    # محاولة تحديد المهمة كمكتملة
    if hasattr(tracker, task_name):
        result = tracker.mark_task_complete(task_name)
        
        if result:
            send_message(chat_id, f"✅ تم تسجيل إكمال مهمة: {task_name}")
            
            # التحقق من اكتمال الجدول
            if tracker.completed:
                send_message(chat_id, "🎉 تهانينا! لقد أكملت جميع مهام جدولك اليوم! +5 نقاط إضافية.")
        else:
            send_message(chat_id, f"ℹ️ المهمة {task_name} مكتملة بالفعل أو غير متاحة.")
    else:
        send_message(chat_id, f"❗ اسم المهمة '{task_name}' غير صحيح. استخدم /schedule لرؤية المهام المتاحة.")
    
    return True

def handle_today_command(user_data):
    """معالجة أمر /today لعرض مهام اليوم"""
    chat_id = user_data['chat_id']
    user_id = user_data['user_id']
    
    # الحصول على المستخدم من قاعدة البيانات
    user = User.query.filter_by(telegram_id=user_id).first()
    
    if not user:
        send_message(chat_id, "❗ حدث خطأ في العثور على بياناتك. يرجى إرسال /start للبدء من جديد.")
        return False
    
    # التحقق من نوع الجدول المفضل للمستخدم
    schedule_type = user.preferred_schedule
    
    if schedule_type == 'none':
        send_message(chat_id, "❗ ليس لديك جدول مفعّل حالياً. استخدم /settings لإعداد جدول.")
        return False
    
    # الحصول على متابعة الجدول ليوم اليوم
    tracker = ScheduleTracker.get_or_create_for_today(user.id, schedule_type)
    
    # إعداد قائمة بجميع المهام ليوم اليوم وحالتها
    today_message = f"<b>📋 مهام اليوم ({datetime.utcnow().strftime('%Y-%m-%d')}):</b>\n\n"
    
    # تحديد المهام حسب نوع الجدول
    if schedule_type == 'morning':
        tasks = [
            ('joined', 'تسجيل الحضور'),
            ('prayer_1', 'صلاة الفجر'),
            ('meal_1', 'الإفطار'),
            ('study_1', 'المذاكرة الأولى'),
            ('prayer_2', 'صلاة الظهر'),
            ('study_2', 'المذاكرة الثانية'),
            ('return_after_break', 'العودة بعد الراحة'),
            ('prayer_3', 'صلاة العصر'),
            ('study_3', 'المراجعة'),
            ('prayer_4', 'صلاة المغرب'),
            ('prayer_5', 'صلاة العشاء'),
            ('evaluation', 'تقييم اليوم')
        ]
    elif schedule_type == 'evening':
        tasks = [
            ('joined', 'تسجيل الحضور'),
            ('study_1', 'المذاكرة الأولى'),
            ('prayer_1', 'صلاة المغرب'),
            ('study_2', 'المذاكرة الثانية'),
            ('prayer_2', 'صلاة العشاء'),
            ('study_3', 'الحفظ/القراءة'),
            ('evaluation', 'تقييم اليوم'),
            ('early_sleep', 'النوم المبكر')
        ]
    elif schedule_type == 'custom':
        # TODO: استخراج المهام من الجدول المخصص
        tasks = [
            ('joined', 'تسجيل الحضور'),
            ('study_1', 'المذاكرة الأولى'),
            ('evaluation', 'تقييم اليوم')
        ]
    
    # إضافة حالة كل مهمة
    completed_count = 0
    for task_name, task_label in tasks:
        task_status = getattr(tracker, task_name, False)
        status_icon = "✅" if task_status else "⬜️"
        today_message += f"{status_icon} {task_label}\n"
        
        if task_status:
            completed_count += 1
    
    # حساب نسبة الإكمال
    completion_percentage = int((completed_count / len(tasks)) * 100)
    progress_bar = generate_progress_bar(completed_count, len(tasks), 10)
    
    today_message += f"\n<b>التقدم اليومي:</b> {progress_bar} {completion_percentage}%"
    
    # إضافة نصيحة إذا لم يتم إكمال جميع المهام
    if completion_percentage < 100:
        today_message += "\n\n💡 استخدم /schedule لرؤية جدولك وتسجيل إكمال المهام."
    else:
        today_message += "\n\n🎉 تهانينا! لقد أكملت جميع مهامك لهذا اليوم!"
    
    # إرسال الرسالة
    send_message(chat_id, today_message, MAIN_MENU)
    
    return True

def handle_report_command(user_data):
    """معالجة أمر /report لعرض تقرير أداء المستخدم"""
    chat_id = user_data['chat_id']
    user_id = user_data['user_id']
    
    # الحصول على المستخدم من قاعدة البيانات
    user = User.query.filter_by(telegram_id=user_id).first()
    
    if not user:
        send_message(chat_id, "❗ حدث خطأ في العثور على بياناتك. يرجى إرسال /start للبدء من جديد.")
        return False
    
    # الحصول على تاريخ بداية الأسبوع (7 أيام مضت)
    start_date = datetime.utcnow().date() - timedelta(days=7)
    
    # الحصول على جميع أنشطة المستخدم خلال الأسبوع
    activities = (
        UserActivity.query
        .filter_by(user_id=user.id)
        .filter(UserActivity.timestamp >= start_date)
        .all()
    )
    
    # الحصول على متابعات الجدول خلال الأسبوع
    trackers = (
        ScheduleTracker.query
        .filter_by(user_id=user.id)
        .filter(ScheduleTracker.date >= start_date)
        .all()
    )
    
    # حساب النقاط الأسبوعية
    weekly_points = sum(activity.points_earned for activity in activities)
    
    # حساب عدد الأيام المكتملة
    completed_days = sum(1 for tracker in trackers if tracker.completed)
    
    # حساب متوسط نقاط اليوم
    avg_daily_points = weekly_points / 7 if activities else 0
    
    # إعداد تقرير الأداء
    report_message = f"""
<b>📊 تقرير أدائك الأسبوعي:</b>

<b>الفترة:</b> من {start_date.strftime('%Y-%m-%d')} إلى {datetime.utcnow().date().strftime('%Y-%m-%d')}

<b>إحصائيات الأسبوع:</b>
• النقاط المكتسبة: {weekly_points} نقطة
• متوسط النقاط اليومية: {round(avg_daily_points, 1)} نقطة
• أيام مكتملة: {completed_days} من 7 أيام
• نسبة الالتزام: {int((completed_days / 7) * 100)}%

<b>توزيع الأنشطة:</b>
"""
    
    # حساب توزيع الأنشطة
    activity_types = {
        'study': 0,
        'prayer': 0,
        'other': 0
    }
    
    for activity in activities:
        if 'study' in activity.activity_type:
            activity_types['study'] += 1
        elif 'prayer' in activity.activity_type:
            activity_types['prayer'] += 1
        else:
            activity_types['other'] += 1
    
    # إضافة توزيع الأنشطة إلى التقرير
    report_message += f"• أنشطة الدراسة: {activity_types['study']}\n"
    report_message += f"• أنشطة الصلاة: {activity_types['prayer']}\n"
    report_message += f"• أنشطة أخرى: {activity_types['other']}\n\n"
    
    # إضافة تعليق تحفيزي بناءً على الأداء
    if completed_days >= 5:
        report_message += "🌟 أداء ممتاز! استمر في المحافظة على هذا المستوى من الالتزام."
    elif completed_days >= 3:
        report_message += "👍 أداء جيد! حاول زيادة التزامك في الأسبوع القادم للوصول إلى مستوى أفضل."
    else:
        report_message += "💪 يمكنك تحسين أدائك! ضع خطة للأسبوع القادم والتزم بها لتحقيق نتائج أفضل."
    
    # إرسال التقرير
    send_message(chat_id, report_message, MAIN_MENU)
    
    return True

def handle_callback_query(callback_data, user_data):
    """معالجة استجابة المستخدم للأزرار التفاعلية"""
    callback_query_id = user_data.get('callback_query_id')
    chat_id = user_data['chat_id']
    user_id = user_data['user_id']
    
    # الحصول على المستخدم من قاعدة البيانات
    user = User.query.filter_by(telegram_id=user_id).first()
    
    if not user:
        send_message(chat_id, "❗ حدث خطأ في العثور على بياناتك. يرجى إرسال /start للبدء من جديد.")
        return False
    
    # معالجة ردود أزرار إدارة قائمة المشرف في المحادثة الخاصة
    if callback_data in ['admin_groups', 'admin_camps', 'create_new_camp', 'customize_camp', 'back_to_main',
                         'personal_schedule', 'group_schedule_select']:
        # التحقق من أن الدردشة خاصة
        if user_data.get('chat_type') == 'private':
            from study_bot.admin_commands import handle_admin_callback_query
            result = handle_admin_callback_query(callback_data, user_data)
            if result:
                return True
                
    # معالجة ردود أزرار إدارة المجموعات والمعسكرات في الخاص
    if callback_data == 'groups_setup' or callback_data.startswith('manage_group:') or callback_data.startswith('group_camps:') or \
       callback_data.startswith('create_camp_setup:') or callback_data.startswith('add_camp_task_setup:') or \
       callback_data == 'confirm_camp_creation' or callback_data == 'confirm_task_creation' or \
       callback_data == 'cancel_setup' or callback_data.startswith('set_schedule_type:') or \
       callback_data.startswith('toggle_motivation:') or callback_data.startswith('send_motivation_now:') or \
       callback_data.startswith('manage_camp:'):
        # التحقق من أن الدردشة خاصة
        if user_data.get('chat_type') == 'private':
            from study_bot.private_camp_manager import handle_private_camp_callbacks
            result = handle_private_camp_callbacks(callback_data, user_id, chat_id, callback_query_id)
            if result:
                return True

    # معالجة ردود أزرار المعسكرات في المجموعة
    if callback_data.startswith('camp_'):
        # التحقق من أن الدردشة مجموعة
        if user_data.get('chat_type') in ['group', 'supergroup']:
            def handle_group_camp_callbacks(data, chat_id, user_id, callback_id):
                """معالجة ردود أزرار معسكرات المجموعات"""
                try:
                    # الانضمام لمعسكر
                    if data.startswith('camp_join:'):
                        from study_bot.custom_camps import handle_camp_join
                        camp_id = int(data.split(':')[1])
                        result = handle_camp_join(camp_id, user_id, callback_id)
                        return True
                        
                    # الانضمام لمهمة معسكر
                    elif data.startswith('camp_task_join:'):
                        from study_bot.custom_camps import handle_camp_task_join
                        task_id = int(data.split(':')[1])
                        result = handle_camp_task_join(task_id, user_id, callback_id)
                        return True
                        
                    # التعامل مع زر معسكر ممتلئ
                    elif data == 'camp_full':
                        from study_bot.group_handlers import answer_callback_query
                        answer_callback_query(callback_id, "⚠️ هذا المعسكر ممتلئ بالفعل")
                        return True
                        
                    return False
                except Exception as e:
                    logger.error(f"خطأ في معالجة ردود أزرار المعسكرات: {e}")
                    return False
                    
            return handle_group_camp_callbacks(callback_data, chat_id, user_id, callback_query_id)
            
    # معالجة الاستجابة حسب نوعها
    if callback_data == 'back_to_main':
        # العودة للقائمة الرئيسية
        return show_main_menu(chat_id)
    elif callback_data == 'my_schedule':
        # عرض الجدول
        handle_schedule_command(user_data)
    elif callback_data == 'my_points':
        # عرض النقاط
        handle_points_command(user_data)
    elif callback_data == 'motivational_message':
        # عرض رسالة تحفيزية
        handle_motivation_command(user_data)
    elif callback_data == 'settings':
        # عرض الإعدادات
        handle_settings_command(user_data)
    elif callback_data == 'help':
        # عرض المساعدة
        handle_help_command(user_data)
    elif callback_data == 'groups_setup':
        # إدارة المجموعات
        from study_bot.private_camp_manager import handle_admin_groups
        handle_admin_groups(user_id, chat_id)
    elif callback_data == 'camps_setup':
        # إدارة المعسكرات الدراسية
        from study_bot.private_camp_manager import handle_admin_camps
        handle_admin_camps(user_id, chat_id)
    # تم التعامل مع 'back_to_main' بالفعل في الأعلى
    elif callback_data == 'back_to_settings':
        # العودة إلى قائمة الإعدادات
        handle_settings_command(user_data)
    elif callback_data == 'change_schedule_type':
        # تغيير نوع الجدول
        change_schedule_message = """
<b>📅 اختر نوع الجدول المفضل:</b>

• <b>الجدول الصباحي</b>: يبدأ من صلاة الفجر وحتى صلاة العشاء
• <b>الجدول المسائي</b>: يبدأ من بعد الظهر وحتى وقت النوم
• <b>جدول مخصص</b>: إنشاء جدول مخصص يناسب ظروفك
• <b>إلغاء الجدول</b>: إيقاف الجدول الحالي
"""
        send_message(chat_id, change_schedule_message, SCHEDULE_TYPE_MENU)
    elif callback_data.startswith('schedule_'):
        # معالجة اختيار نوع الجدول
        schedule_type = callback_data.replace('schedule_', '')
        handle_schedule_selection(user, chat_id, schedule_type)
    elif callback_data == 'notification_settings':
        # إعدادات الإشعارات
        notification_settings_message = """
<b>🔔 إعدادات الإشعارات:</b>

اختر أحد الخيارات أدناه لتعديل إعدادات الإشعارات:
"""
        send_message(chat_id, notification_settings_message, NOTIFICATION_SETTINGS_MENU)
    elif callback_data == 'toggle_smart_notifications':
        # تفعيل/إيقاف محسن الإشعارات الذكي
        new_status = not user.smart_notifications_enabled
        user.update_smart_notifications_settings(enabled=new_status)
        status_text = "تفعيل" if new_status else "إيقاف"
        send_message(chat_id, f"✅ تم {status_text} محسن الإشعارات الذكي بنجاح.")
    elif callback_data == 'set_notification_sensitivity':
        # ضبط حساسية توقيت الإشعارات
        sensitivity_menu = {
            'inline_keyboard': [
                [{'text': 'منخفضة (أقل إشعارات)', 'callback_data': 'sensitivity_1'}],
                [{'text': 'متوسطة (الإعداد الافتراضي)', 'callback_data': 'sensitivity_2'}],
                [{'text': 'عالية (إشعارات أكثر دقة)', 'callback_data': 'sensitivity_3'}],
                [{'text': '🔙 رجوع', 'callback_data': 'back_to_notification_settings'}]
            ]
        }
        send_message(chat_id, "<b>🕓 اختر مستوى حساسية توقيت الإشعارات:</b>", sensitivity_menu)
    elif callback_data.startswith('sensitivity_'):
        # تعيين مستوى الحساسية
        sensitivity = int(callback_data.replace('sensitivity_', ''))
        user.update_smart_notifications_settings(sensitivity=sensitivity)
        send_message(chat_id, f"✅ تم ضبط حساسية توقيت الإشعارات إلى المستوى {sensitivity} بنجاح.")
    elif callback_data == 'set_max_notifications':
        # ضبط الحد الأقصى للإشعارات اليومية
        max_notifications_menu = {
            'inline_keyboard': [
                [{'text': '5 إشعارات', 'callback_data': 'max_notif_5'}],
                [{'text': '10 إشعارات (الافتراضي)', 'callback_data': 'max_notif_10'}],
                [{'text': '15 إشعار', 'callback_data': 'max_notif_15'}],
                [{'text': '20 إشعار', 'callback_data': 'max_notif_20'}],
                [{'text': '🔙 رجوع', 'callback_data': 'back_to_notification_settings'}]
            ]
        }
        send_message(chat_id, "<b>🔢 اختر الحد الأقصى للإشعارات اليومية:</b>", max_notifications_menu)
    elif callback_data.startswith('max_notif_'):
        # تعيين الحد الأقصى للإشعارات
        max_notif = int(callback_data.replace('max_notif_', ''))
        user.update_smart_notifications_settings(max_daily=max_notif)
        send_message(chat_id, f"✅ تم ضبط الحد الأقصى للإشعارات اليومية إلى {max_notif} إشعارات بنجاح.")
    elif callback_data == 'back_to_notification_settings':
        # العودة إلى إعدادات الإشعارات
        notification_settings_message = "<b>🔔 إعدادات الإشعارات:</b>"
        send_message(chat_id, notification_settings_message, NOTIFICATION_SETTINGS_MENU)
    elif callback_data == 'toggle_motivation':
        # تفعيل/إيقاف الرسائل التحفيزية
        new_status = not user.motivation_enabled
        user.motivation_enabled = new_status
        db.session.commit()
        status_text = "تفعيل" if new_status else "إيقاف"
        send_message(chat_id, f"✅ تم {status_text} الرسائل التحفيزية بنجاح.")
    elif callback_data.startswith('complete_'):
        # تسجيل إكمال مهمة
        task_name = callback_data.replace('complete_', '')
        handle_task_completion(user, chat_id, task_name)
    
    # إجابة على نداء الاستجابة (تختفي الإشارة الزرقاء)
    if callback_query_id:
        answer_callback_query(callback_query_id)
    
    return True

def handle_schedule_selection(user, chat_id, schedule_type):
    """معالجة اختيار نوع الجدول"""
    # تحديث نوع الجدول المفضل للمستخدم
    prev_schedule_type = user.preferred_schedule
    user.preferred_schedule = schedule_type
    db.session.commit()
    
    if schedule_type == 'none':
        # إلغاء الجدول
        send_message(chat_id, "✅ تم إلغاء الجدول بنجاح. يمكنك اختيار جدول جديد في أي وقت.")
        return
    
    # إنشاء أو تحديث جدول المستخدم
    if schedule_type != 'custom':
        UserSchedule.create_or_update(user.id, schedule_type)
    
    # الإجراءات الخاصة بالجدول المخصص
    if schedule_type == 'custom':
        custom_schedule_message = """
<b>✏️ الجدول المخصص:</b>

لإنشاء جدول مخصص، يرجى اتباع الخطوات التالية:

1. أرسل رسالة تبدأ بـ <code>/custom_schedule</code> متبوعة بقائمة المهام

<b>مثال:</b>
<code>/custom_schedule
task1: المهمة الأولى, 08:00
task2: المهمة الثانية, 10:30
prayer_1: صلاة الظهر, 12:30
study_1: المذاكرة, 14:00</code>

يمكنك إضافة وقت لكل مهمة كما هو موضح في المثال.
"""
        send_message(chat_id, custom_schedule_message)
    else:
        # رسالة تأكيد اختيار الجدول
        schedule_name = {
            'morning': 'الصباحي',
            'evening': 'المسائي'
        }.get(schedule_type, '')
        
        confirmation_message = f"""
✅ تم تفعيل الجدول {schedule_name} بنجاح!

استخدم أمر /schedule لعرض تفاصيل جدولك الجديد.
"""
        send_message(chat_id, confirmation_message)
        
        # تسجيل نشاط انضمام إذا كان جدول جديد أو مختلف عن السابق
        if prev_schedule_type != schedule_type:
            tracker = ScheduleTracker.get_or_create_for_today(user.id, schedule_type)
            tracker.mark_task_complete('joined')

def handle_task_completion(user, chat_id, task_name):
    """معالجة تسجيل إكمال مهمة"""
    # التحقق من نوع الجدول المفضل للمستخدم
    schedule_type = user.preferred_schedule
    
    if schedule_type == 'none':
        send_message(chat_id, "❗ ليس لديك جدول مفعّل حالياً. استخدم /settings لإعداد جدول.")
        return
    
    # الحصول على متابعة الجدول ليوم اليوم
    tracker = ScheduleTracker.get_or_create_for_today(user.id, schedule_type)
    
    # محاولة تحديد المهمة كمكتملة
    if hasattr(tracker, task_name) and not getattr(tracker, task_name):
        result = tracker.mark_task_complete(task_name)
        
        if result:
            # تحديث الجدول بعد إكمال المهمة
            handle_schedule_command({'chat_id': chat_id, 'user_id': user.telegram_id})
            
            # التحقق من اكتمال الجدول
            if tracker.completed:
                send_message(chat_id, "🎉 تهانينا! لقد أكملت جميع مهام جدولك اليوم!")
        else:
            send_message(chat_id, f"ℹ️ المهمة {task_name} غير متاحة.")
    else:
        # المهمة مكتملة بالفعل، إعادة عرض الجدول
        handle_schedule_command({'chat_id': chat_id, 'user_id': user.telegram_id})

def answer_callback_query(callback_query_id, text=None, show_alert=False):
    """الإجابة على نداء الاستجابة"""
    url = f"{TELEGRAM_API_URL}/answerCallbackQuery"
    payload = {'callback_query_id': callback_query_id}
    
    if text:
        payload['text'] = text
    
    if show_alert:
        payload['show_alert'] = True
    
    try:
        response = requests.post(url, json=payload)
        return response.json().get('ok', False)
    except Exception as e:
        logger.error(f"استثناء عند الإجابة على نداء الاستجابة: {e}")
        return False

def send_broadcast_message(message_text):
    """إرسال رسالة جماعية لجميع المستخدمين النشطين"""
    # الحصول على جميع المستخدمين النشطين
    users = User.query.filter_by(is_active=True).all()
    
    if not users:
        return {'success': 0, 'fail': 0, 'error': 'لا يوجد مستخدمون نشطون'}
    
    success_count = 0
    fail_count = 0
    
    for user in users:
        try:
            result = send_message(user.telegram_id, message_text)
            if result:
                success_count += 1
            else:
                fail_count += 1
        except Exception as e:
            logger.error(f"خطأ في إرسال رسالة جماعية للمستخدم {user.telegram_id}: {e}")
            fail_count += 1
    
    return {
        'success': success_count,
        'fail': fail_count
    }

def handle_message(message_data, app_context):
    """معالجة الرسائل الواردة من المستخدمين"""
    try:
        with app_context():
            message = message_data.get('message', {})
            callback_query = message_data.get('callback_query', {})
            
            # معالجة الأزرار التفاعلية
            if callback_query:
                callback_data = callback_query.get('data', '')
                message = callback_query.get('message', {})
                chat = message.get('chat', {})
                chat_type = chat.get('type', 'private')
                
                user_data = {
                    'user_id': callback_query.get('from', {}).get('id'),
                    'username': callback_query.get('from', {}).get('username'),
                    'first_name': callback_query.get('from', {}).get('first_name'),
                    'last_name': callback_query.get('from', {}).get('last_name'),
                    'chat_id': chat.get('id'),
                    'message_id': message.get('message_id'),
                    'callback_query_id': callback_query.get('id')
                }
                
                # التحقق من نوع الدردشة (خاص أو مجموعة)
                if chat_type in ['group', 'supergroup']:
                    user_data['group_title'] = chat.get('title', 'Group')
                    
                    # معالجة أزرار المجموعة
                    from study_bot.group_handlers import handle_group_callback
                    # معالجة استجابات المجموعة إذا بدأت بـ group_ أو join_
                    if callback_data.startswith('group_') or callback_data.startswith('join_'):
                        return handle_group_callback(callback_data, user_data)
                
                # معالجة أزرار إنشاء المعسكر
                from study_bot.private_camp_manager import handle_private_camp_callbacks
                if chat_type == 'private' and (callback_data.startswith('camp_') or callback_data.startswith('new_camp')):
                    user_id = user_data['user_id']
                    chat_id = user_data['chat_id']
                    callback_query_id = user_data['callback_query_id']
                    if handle_private_camp_callbacks(callback_data, user_id, chat_id, callback_query_id):
                        return True
                
                # معالجة الأزرار العادية للمستخدمين
                return handle_callback_query(callback_data, user_data)
            
            # معالجة الرسائل النصية
            if message:
                text = message.get('text', '')
                user = message.get('from', {})
                chat = message.get('chat', {})
                chat_type = chat.get('type', 'private')
                chat_id = chat.get('id')
                user_id = user.get('id')
                
                if not text:
                    return False
                
                user_data = {
                    'user_id': user_id,
                    'username': user.get('username'),
                    'first_name': user.get('first_name'),
                    'last_name': user.get('last_name'),
                    'chat_id': chat_id,
                    'text': text
                }
                
                # إضافة معلومات المجموعة إذا كانت الدردشة مجموعة
                if chat_type in ['group', 'supergroup']:
                    user_data['chat_type'] = 'group'
                    user_data['group_title'] = chat.get('title', 'Group')
                else:
                    user_data['chat_type'] = 'private'
                    # التحقق من حالة إنشاء المعسكر
                    from study_bot.private_camp_manager import private_setup_states, process_camp_creation_input
                    if user_id in private_setup_states:
                        current_state = private_setup_states[user_id]
                        # معالجة مدخلات إنشاء المعسكر
                        if current_state.startswith('waiting_camp_'):
                            process_camp_creation_input(user_id, chat_id, text, current_state)
                            return True
                
                # معالجة الأوامر
                if text.startswith('/'):
                    # التعامل مع الأوامر مع اسم البوت (مثل /start@BotName)
                    command_full = text.split(maxsplit=1)[0].lower()
                    if '@' in command_full:
                        command_parts = command_full.split('@')
                        command = command_parts[0].lower()
                        bot_name = command_parts[1].lower()
                        
                        # التحقق من أن الأمر موجه لهذا البوت
                        if bot_name != 'study_schedule501_bot':
                            return False
                    else:
                        command = command_full
                    
                    # تقسيم الأمر للحصول على الوسائط
                    text_parts = text.split(maxsplit=1)
                    command_args = text_parts[1].split() if len(text_parts) > 1 else []
                    
                    # معالجة أوامر المجموعة
                    if chat_type in ['group', 'supergroup']:
                        from study_bot.group_handlers import handle_group_start
                        
                        if command == '/start':
                            # التحقق من صلاحيات البوت قبل الرد
                            if not check_bot_admin_status(chat.get('id')):
                                send_message(chat.get('id'), """⚠️ <b>تنبيه!</b>\n\nلكي يعمل البوت بشكل صحيح في المجموعة، يجب أن يكون مشرفًا مع الصلاحيات التالية:\n\n- إرسال الرسائل\n- حذف الرسائل\n- تثبيت الرسائل\n- إضافة أعضاء\n\nيرجى إضافة البوت كمشرف ثم إرسال أمر /start مرة أخرى.""")
                                return True
                            return handle_group_start(user_data)
                        # معالجة أوامر المعسكرات المخصصة
                        elif command in ['/create_camp', '/add_camp_task', '/camp_report', '/camp_help']:
                            # تأكد من أن البوت مشرف قبل معالجة أوامر المعسكر
                            if not check_bot_admin_status(chat.get('id')):
                                send_message(chat.get('id'), """⚠️ <b>تنبيه!</b>\n\nلكي يعمل البوت بشكل صحيح في المجموعة، يجب أن يكون مشرفًا.""") 
                                return True
                                
                            # استدعاء معالج أوامر المعسكرات
                            def handle_group_camp_commands(message, chat_id, user_id):
                                """معالجة أوامر المعسكرات المخصصة في المجموعات"""
                                try:
                                    # الحصول على الأمر والنص
                                    command_parts = message.split(maxsplit=1)
                                    command = command_parts[0].lower() if command_parts else ''
                                    command_text = command_parts[1] if len(command_parts) > 1 else ''
                                    
                                    # أمر إنشاء معسكر جديد
                                    if command == '/create_camp':
                                        from study_bot.custom_camps import handle_create_camp_command
                                        result = handle_create_camp_command(chat_id, user_id, command_text)
                                        send_message(chat_id, result)
                                        return True
                                        
                                    # أمر إضافة مهمة لمعسكر
                                    elif command == '/add_camp_task':
                                        from study_bot.custom_camps import handle_add_camp_task_command
                                        result = handle_add_camp_task_command(chat_id, user_id, command_text)
                                        send_message(chat_id, result)
                                        return True
                                        
                                    # أمر طلب تقرير معسكر
                                    elif command == '/camp_report':
                                        from study_bot.custom_camps import handle_camp_report_command
                                        result = handle_camp_report_command(chat_id, user_id, command_text)
                                        send_message(chat_id, result)
                                        return True
                                        
                                    # أمر مساعدة المعسكرات
                                    elif command == '/camp_help':
                                        help_text = """
🔍 <b>أوامر المعسكرات الدراسية</b>

/create_camp <اسم المعسكر> | <وصف المعسكر> | <تاريخ البداية YYYY-MM-DD> | <تاريخ النهاية YYYY-MM-DD> | [الحد الأقصى للمشاركين]
➡️ إنشاء معسكر دراسي جديد (للمشرفين فقط)

/add_camp_task <رقم المعسكر> | <عنوان المهمة> | <وصف المهمة> | <وقت الجدولة YYYY-MM-DD HH:MM> | <النقاط> | [المهلة بالدقائق]
➡️ إضافة مهمة لمعسكر موجود (للمشرفين فقط)

/camp_report [رقم المعسكر]
➡️ عرض تقرير عن معسكر معين أو عرض قائمة المعسكرات المتاحة

/camp_help
➡️ عرض هذه المساعدة
"""
                                        send_message(chat_id, help_text)
                                        return True
                                        
                                    return False
                                except Exception as e:
                                    logger.error(f"خطأ في معالجة أوامر المعسكرات: {e}")
                                    return False
                                    
                            user_id = message.get('from', {}).get('id')
                            return handle_group_camp_commands(text, chat.get('id'), user_id)
                                
                        # أوامر مجموعة أخرى
                        elif command == '/help':
                            help_message = f"""
📚 <b>مساعدة بوت جدولة الدراسة والتحفيز للمجموعات</b>

يساعد هذا البوت المجموعات على تنظيم جلسات الدراسة الجماعية ومتابعة تقدم الأعضاء.

<b>الأوامر المتاحة:</b>

• /start - بدء البوت وعرض قائمة الإعدادات
• /help - عرض هذه الرسالة
• /developer - معلومات عن مطور البوت

<b>الميزات الرئيسية:</b>

• جداول دراسة صباحية ومسائية
• نظام نقاط تحفيزي
• تقارير يومية للمشاركين
• رسائل تحفيزية دورية
• ترتيب المتفوقين بالنقاط

<b>ملاحظة:</b> يجب أن يكون البوت مشرفًا في المجموعة لكي يعمل بشكل صحيح.

للمزيد من المساعدة، تواصل مع المطور @M_o_h_a_m_e_d_501
"""
                            send_message(chat.get('id'), help_message)
                            return True
                        elif command == '/developer':
                            developer_message = """👨‍💻 <b>مطور البوت</b>\n\nتم تطوير بوت جدولة الدراسة والتحفيز بواسطة: @M_o_h_a_m_e_d_501\n\nلأي استفسارات أو اقتراحات، يرجى التواصل معه.\n\n🌟 جميع الحقوق محفوظة © 2025"""
                            send_message(chat.get('id'), developer_message)
                            return True
                    
                    # معالجة أوامر المستخدم في المحادثة الخاصة
                    # أولا: التحقق من أوامر المشرف في المحادثة الخاصة
                    if chat.get('type') == 'private':
                        if command == '/groups':
                            from study_bot.admin_commands import handle_groups_command
                            return handle_groups_command(user_data)
                        elif command == '/camps':
                            from study_bot.admin_commands import handle_camps_command
                            return handle_camps_command(user_data)
                        elif command == '/newcamp':
                            from study_bot.admin_commands import handle_newcamp_command
                            return handle_newcamp_command(user_data)
                        elif command == '/customcamp':
                            from study_bot.admin_commands import handle_customcamp_command
                            return handle_customcamp_command(user_data)
                        elif command == '/grouphelp':
                            from study_bot.admin_commands import handle_grouphelp_command
                            return handle_grouphelp_command(user_data)
                        elif command == '/schedule':
                            # التحقق إذا كان المستخدم مشرف مجموعة
                            from study_bot.admin_commands import handle_admin_schedule_command
                            user_id = user_data['user_id']
                            admin_groups = Group.query.filter_by(admin_id=user_id).all()
                            if admin_groups:
                                # هذا مشرف ، عرض قائمة للاختيار بين الجدول الشخصي وجدول المجموعة
                                return handle_admin_schedule_command(user_data)
                    
                    # معالجة أوامر المستخدم العادية
                    if command == '/start':
                        return handle_start_command(user_data)
                    elif command == '/help':
                        return handle_help_command(user_data)
                    elif command == '/developer':
                        developer_message = """👨‍💻 <b>مطور البوت</b>\n\nتم تطوير بوت جدولة الدراسة والتحفيز بواسطة: @M_o_h_a_m_e_d_501\n\nلأي استفسارات أو اقتراحات، يرجى التواصل معه.\n\n🌟 جميع الحقوق محفوظة © 2025"""
                        send_message(chat.get('id'), developer_message)
                        return True
                    elif command == '/schedule':
                        return handle_schedule_command(user_data)
                    elif command == '/points':
                        return handle_points_command(user_data)
                    elif command == '/motivation':
                        return handle_motivation_command(user_data)
                    elif command == '/settings':
                        return handle_settings_command(user_data)
                    elif command == '/done':
                        return handle_done_command(user_data, command_args)
                    elif command == '/today':
                        return handle_today_command(user_data)
                    elif command == '/report':
                        return handle_report_command(user_data)
                    elif command == '/custom_schedule' and len(command_args) > 0:
                        # معالجة الجدول المخصص
                        return handle_custom_schedule(user_data, command_args)
                    elif command == '/custom_task' and len(command_args) > 0:
                        # معالجة المهمة المخصصة
                        chat_id = chat.get('id')
                        from_user = message.get('from', {})
                        user_id = from_user.get('id')
                        
                        # التحقق من نوع الدردشة
                        if chat.get('type') in ['group', 'supergroup']:
                            # استدعاء وظيفة معالجة مهمة المجموعة
                            from study_bot.group_tasks import handle_custom_task_command
                            
                            # معالجة الأمر
                            group = Group.query.filter_by(telegram_id=chat_id).first()
                            if group:
                                response = handle_custom_task_command(group.id, user_id, command_args)
                                send_message(chat_id, response)
                                return True
                            else:
                                send_message(chat_id, "❌ لم يتم العثور على المجموعة في قاعدة البيانات. استخدم أمر /start لتهيئة المجموعة.")
                                return True
                        else:
                            # إذا كان في محادثة خاصة
                            send_message(chat_id, "❌ هذا الأمر متاح فقط في المجموعات.")
                            return True
                
                # معالجة الرسائل العادية
                # TODO: يمكن إضافة وظائف أخرى لمعالجة الرسائل العادية
            
            return False
    
    except Exception as e:
        logger.error(f"استثناء عند معالجة الرسالة: {e}\n{traceback.format_exc()}")
        return False

def check_bot_admin_status(chat_id):
    """التحقق من حالة البوت كمشرف في المجموعة"""
    url = f"{TELEGRAM_API_URL}/getChatMember"
    payload = {
        'chat_id': chat_id,
        'user_id': int(TELEGRAM_BOT_TOKEN.split(':')[0])  # معرف البوت
    }
    
    try:
        response = requests.post(url, json=payload)
        result = response.json()
        
        if response.status_code == 200 and result.get('ok'):
            status = result['result'].get('status')
            # التحقق من أن البوت مشرف
            return status in ['administrator', 'creator']
        else:
            logger.error(f"خطأ في التحقق من حالة البوت كمشرف: {result}")
            return False
    except Exception as e:
        logger.error(f"استثناء عند التحقق من حالة البوت كمشرف: {e}")
        return False

def handle_custom_schedule(user_data, schedule_text):
    """معالجة إنشاء جدول مخصص"""
    chat_id = user_data['chat_id']
    user_id = user_data['user_id']
    
    # الحصول على المستخدم من قاعدة البيانات
    user = User.query.filter_by(telegram_id=user_id).first()
    
    if not user:
        send_message(chat_id, "❗ حدث خطأ في العثور على بياناتك. يرجى إرسال /start للبدء من جديد.")
        return False
    
    try:
        # تحليل نص الجدول المخصص
        custom_schedule = {}
        lines = schedule_text.strip().split('\n')
        
        for line in lines:
            if ':' not in line:
                continue
            
            task_parts = line.split(':', 1)
            task_key = task_parts[0].strip()
            
            task_details_parts = task_parts[1].strip().split(',', 1)
            task_name = task_details_parts[0].strip()
            task_time = task_details_parts[1].strip() if len(task_details_parts) > 1 else None
            
            custom_schedule[task_key] = {
                'name': task_name,
                'time': task_time
            }
        
        if not custom_schedule:
            send_message(chat_id, "❗ تنسيق الجدول المخصص غير صحيح. يرجى اتباع المثال المقدم.")
            return False
        
        # تحديث الجدول المخصص للمستخدم
        user.preferred_schedule = 'custom'
        db.session.commit()
        
        UserSchedule.create_or_update(
            user_id=user.id,
            schedule_type='custom',
            is_custom=True,
            custom_schedule=custom_schedule
        )
        
        # تأكيد إنشاء الجدول المخصص
        confirmation_message = f"""
✅ تم إنشاء الجدول المخصص بنجاح!

تم إضافة {len(custom_schedule)} مهمة إلى جدولك.
استخدم أمر /schedule لعرض تفاصيل جدولك الجديد.
"""
        send_message(chat_id, confirmation_message)
        
        return True
    
    except Exception as e:
        logger.error(f"خطأ في معالجة الجدول المخصص: {e}")
        send_message(chat_id, "❗ حدث خطأ أثناء إنشاء الجدول المخصص. يرجى المحاولة مرة أخرى.")
        return False

def fetch_updates(offset=None):
    """الحصول على التحديثات من واجهة برمجة تطبيقات تيليجرام"""
    url = f"{TELEGRAM_API_URL}/getUpdates"
    params = {
        'timeout': 30,
        'allowed_updates': ['message', 'callback_query']
    }
    
    if offset is not None:
        params['offset'] = offset
    
    try:
        response = requests.get(url, params=params)
        return response.json()
    except Exception as e:
        logger.error(f"استثناء عند جلب التحديثات: {e}")
        return {'ok': False, 'description': str(e)}

def bot_polling_loop(app):
    """حلقة استطلاع لتلقي التحديثات من واجهة برمجة تطبيقات تيليجرام"""
    logger.info("بدء حلقة استطلاع بوت تيليجرام")
    offset = None
    
    while True:
        try:
            updates = fetch_updates(offset)
            
            if not updates.get('ok', False):
                logger.error(f"خطأ في الحصول على التحديثات: {updates.get('description', 'خطأ غير معروف')}")
                continue
            
            results = updates.get('result', [])
            
            for update in results:
                update_id = update.get('update_id')
                
                # معالجة الرسالة مع تمرير سياق التطبيق
                handle_message(update, app.app_context)
                
                # تحديث الأوفست للحصول على الرسائل الجديدة فقط
                offset = update_id + 1
            
        except Exception as e:
            logger.error(f"استثناء في حلقة الاستطلاع: {e}\n{traceback.format_exc()}")
        
        # تأخير قصير لتجنب استهلاك موارد النظام
        import time
        time.sleep(1)

def run_bot(app, in_thread=True):
    """تشغيل بوت تيليجرام"""
    global _bot
    
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "dummy_token_for_web_only":
        logger.error("TOKEN غير موجود! لا يمكن تشغيل البوت.")
        return None
    
    logger.info("بدء تشغيل بوت تيليجرام...")
    
    # تعيين كائن البوت العمومي
    _bot = {
        'token': TELEGRAM_BOT_TOKEN,
        'url': TELEGRAM_API_URL
    }
    
    if in_thread:
        # تشغيل البوت في خيط منفصل
        thread = threading.Thread(target=bot_polling_loop, args=(app,))
        thread.daemon = True
        thread.start()
        logger.info("تم بدء خيط البوت بنجاح")
        return thread
    else:
        # تشغيل البوت في الخيط الرئيسي (غير مستحسن)
        bot_polling_loop(app)
        return None
