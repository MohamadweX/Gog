#!/usr/bin/env python3
"""
معالج الرسائل الخاصة
يحتوي على وظائف لمعالجة الرسائل في المحادثات الخاصة
"""

import json
from datetime import datetime

from study_bot.bot import send_message
from study_bot.models import User
from study_bot.config import logger

def create_main_menu_keyboard():
    """إنشاء لوحة مفاتيح القائمة الرئيسية"""
    return {
        "inline_keyboard": [
            [
                {"text": "جدولي الدراسي 📅", "callback_data": "schedule"}
            ],
            [
                {"text": "نقاطي 🏆", "callback_data": "points"},
                {"text": "تحفيز 💪", "callback_data": "motivation"}
            ],
            [
                {"text": "الإعدادات ⚙️", "callback_data": "settings"},
                {"text": "المساعدة ❓", "callback_data": "help"}
            ]
        ]
    }

def show_main_menu(chat_id):
    """عرض القائمة الرئيسية للمستخدم"""
    keyboard = create_main_menu_keyboard()
    return send_message(
        chat_id,
        "مرحباً بك في بوت الدراسة والتحفيز! اختر من القائمة أدناه:",
        reply_markup=keyboard
    )

def handle_start_command(user_id, chat_id):
    """معالجة أمر /start"""
    # إنشاء أو تحديث مستخدم
    User.get_or_create(telegram_id=user_id)
    
    # عرض رسالة الترحيب والقائمة الرئيسية
    welcome_message = """
مرحباً بك في <b>بوت الدراسة والتحفيز</b>! 📚

هذا البوت يساعدك على:
- الالتزام بجدول دراسي منتظم 📅
- المشاركة في معسكرات دراسية جماعية ⛺
- تلقي رسائل تحفيزية لمساعدتك على الاستمرار 💪

استخدم الأزرار أدناه للبدء أو اكتب /help لمزيد من المعلومات.
يمكنك أيضًا إضافة البوت إلى مجموعة لتفعيل الدراسة الجماعية!
"""
    send_message(chat_id, welcome_message)
    return show_main_menu(chat_id)

def handle_help_command(user_id, chat_id):
    """معالجة أمر /help"""
    help_text = """
<b>مساعدة بوت الدراسة والتحفيز</b> 📖

<b>الأوامر الأساسية:</b>
/start - بدء البوت وعرض القائمة الرئيسية
/help - عرض هذه الرسالة
/schedule - عرض الجدول الدراسي
/points - عرض نقاطك
/motivation - الحصول على رسالة تحفيزية
/settings - إعدادات المستخدم
/done - تسجيل إكمال مهمة
/today - عرض مهام اليوم
/report - عرض تقرير أدائك


<b>أوامر المجموعات:</b>
/grouphelp - عرض مساعدة المجموعات

<b>معسكرات الدراسة:</b>
المعسكرات هي جداول دراسية جماعية مؤقتة لفترة محددة.
يمكن لمشرفي المجموعات إنشاء معسكرات مخصصة لأعضاء المجموعة.
"""
    return send_message(chat_id, help_text)

def handle_schedule_command(user_id, chat_id):
    """معالجة أمر /schedule"""
    schedule_text = """
<b>الجدول الدراسي</b> 📅

<b>اختر نوع الجدول:</b>
- الجدول الصباحي ☀️
- الجدول المسائي 🌙
- جدول مخصص ⚙️

<i>يمكنك تعديل الجدول وإضافة مهام من خلال الإعدادات.</i>
"""
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "الجدول الصباحي ☀️", "callback_data": "schedule_morning"}
            ],
            [
                {"text": "الجدول المسائي 🌙", "callback_data": "schedule_evening"}
            ],
            [
                {"text": "جدول مخصص ⚙️", "callback_data": "schedule_custom"}
            ],
            [
                {"text": "العودة للقائمة الرئيسية 🏠", "callback_data": "back_to_main"}
            ]
        ]
    }
    return send_message(chat_id, schedule_text, reply_markup=keyboard)

def handle_points_command(user_id, chat_id):
    """معالجة أمر /points"""
    # هنا يمكن إضافة منطق لحساب النقاط من قاعدة البيانات
    points_text = """
<b>نقاطك</b> 🏆

- النقاط الحالية: 0 نقطة
- المستوى: مبتدئ 🌱
- أيام متتالية: 0 يوم

<i>أكمل المزيد من المهام للحصول على نقاط وترقية مستواك!</i>
"""
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "المتصدرون 🥇", "callback_data": "leaderboard"}
            ],
            [
                {"text": "العودة للقائمة الرئيسية 🏠", "callback_data": "back_to_main"}
            ]
        ]
    }
    return send_message(chat_id, points_text, reply_markup=keyboard)

def handle_motivation_command(user_id, chat_id):
    """معالجة أمر /motivation"""
    motivation_text = """
<b>رسالة تحفيزية</b> 💪

"النجاح ليس نهائياً، والفشل ليس قاتلاً: إنما الشجاعة للاستمرار هي ما يهم."
- ونستون تشرشل

<i>استمر في العمل الجاد، وستصل إلى هدفك!</i>
"""
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "رسالة أخرى 🔄", "callback_data": "more_motivation"}
            ],
            [
                {"text": "العودة للقائمة الرئيسية 🏠", "callback_data": "back_to_main"}
            ]
        ]
    }
    return send_message(chat_id, motivation_text, reply_markup=keyboard)

def handle_settings_command(user_id, chat_id):
    """معالجة أمر /settings"""
    settings_text = """
<b>الإعدادات</b> ⚙️

يمكنك تعديل إعدادات الحساب والإشعارات من هنا.
"""
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "إعدادات الجدول 📅", "callback_data": "settings_schedule"}
            ],
            [
                {"text": "إعدادات الإشعارات 🔔", "callback_data": "settings_notifications"}
            ],
            [
                {"text": "العودة للقائمة الرئيسية 🏠", "callback_data": "back_to_main"}
            ]
        ]
    }
    return send_message(chat_id, settings_text, reply_markup=keyboard)

def handle_today_command(user_id, chat_id):
    """معالجة أمر /today"""
    today_text = """
<b>مهام اليوم</b> 📋

<i>ليس لديك مهام فعالة اليوم. استخدم أمر /schedule لإعداد جدول دراسي.</i>
"""
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "إعداد جدول 📅", "callback_data": "schedule"}
            ],
            [
                {"text": "العودة للقائمة الرئيسية 🏠", "callback_data": "back_to_main"}
            ]
        ]
    }
    return send_message(chat_id, today_text, reply_markup=keyboard)

def handle_report_command(user_id, chat_id):
    """معالجة أمر /report"""
    report_text = """
<b>تقرير الأداء</b> 📊

📈 <b>إحصائيات الأسبوع:</b>
- المهام المكتملة: 0
- ساعات الدراسة: 0
- متوسط الالتزام: 0%

<i>استخدم أمر /schedule لإعداد جدول دراسي وتحسين أدائك!</i>
"""
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "تقرير شهري 📆", "callback_data": "report_monthly"}
            ],
            [
                {"text": "العودة للقائمة الرئيسية 🏠", "callback_data": "back_to_main"}
            ]
        ]
    }
    return send_message(chat_id, report_text, reply_markup=keyboard)

def handle_done_command(user_id, chat_id, command_args):
    """معالجة أمر /done"""
    if not command_args:
        done_text = """
<b>تسجيل إكمال مهمة</b> ✅

الرجاء تحديد اسم المهمة بعد الأمر، مثال:
/done قراءة الفصل الأول
"""
        return send_message(chat_id, done_text)
    
    task_name = " ".join(command_args)
    done_text = f"""
<b>تم تسجيل إكمال المهمة!</b> ✅

المهمة: {task_name}
الوقت: {datetime.now().strftime('%H:%M:%S')}

<i>أحسنت! استمر في العمل الجاد!</i>
"""
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "عرض مهام اليوم 📋", "callback_data": "today"}
            ],
            [
                {"text": "العودة للقائمة الرئيسية 🏠", "callback_data": "back_to_main"}
            ]
        ]
    }
    return send_message(chat_id, done_text, reply_markup=keyboard)

def handle_private_message(message):
    """معالجة رسالة في الخاص"""
    # تحديث معلومات المستخدم
    user_id = message.get("from", {}).get("id")
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")
    username = message.get("from", {}).get("username")
    first_name = message.get("from", {}).get("first_name")
    last_name = message.get("from", {}).get("last_name")
    
    # الحصول على المستخدم أو إنشاء مستخدم جديد
    User.get_or_create(
        telegram_id=user_id,
        username=username,
        first_name=first_name,
        last_name=last_name
    )
    
    # معالجة الأوامر
    if text.startswith('/'):
        command = text.split()[0].lower()
        command_args = text.split()[1:] if len(text.split()) > 1 else []
        
        # توجيه الأمر للمعالج المناسب
        if command == '/start':
            return handle_start_command(user_id, chat_id)
        elif command == '/help':
            return handle_help_command(user_id, chat_id)
        elif command == '/schedule':
            return handle_schedule_command(user_id, chat_id)
        elif command == '/points':
            return handle_points_command(user_id, chat_id)
        elif command == '/motivation':
            return handle_motivation_command(user_id, chat_id)
        elif command == '/settings':
            return handle_settings_command(user_id, chat_id)
        elif command == '/today':
            return handle_today_command(user_id, chat_id)
        elif command == '/report':
            return handle_report_command(user_id, chat_id)
        elif command == '/done':
            return handle_done_command(user_id, chat_id, command_args)
        else:
            return send_message(chat_id, f"عذرًا، الأمر <b>{command}</b> غير معروف. يمكنك استخدام /help لمعرفة الأوامر المتاحة.")
    
    # معالجة الرسائل العادية
    return send_message(chat_id, "مرحباً! يمكنك استخدام الأوامر من القائمة أدناه:", reply_markup=create_main_menu_keyboard())
