#!/usr/bin/env python3
"""
معالج رسائل المجموعات
يحتوي على وظائف لمعالجة الرسائل في المجموعات
"""

import json
from datetime import datetime

from study_bot.bot import send_message
from study_bot.models import User
from study_bot.config import logger

def create_group_setup_keyboard():
    """إنشاء لوحة مفاتيح إعداد المجموعة"""
    return {
        "inline_keyboard": [
            [
                {"text": "إعداد المجموعة هنا ⚙️", "callback_data": "group_setup_here"}
            ],
            [
                {"text": "إعداد المجموعة في الخاص 🔐", "callback_data": "group_setup_private"}
            ]
        ]
    }

def handle_group_start(chat_id, user_id):
    """معالجة أمر /start في المجموعة"""
    welcome_message = """
مرحباً بكم في <b>بوت الدراسة والتحفيز</b>! 📚

هذا البوت يساعد مجموعتكم على:
- تنظيم جداول دراسية جماعية 📅
- إنشاء معسكرات دراسية ⛺
- إرسال رسائل تحفيزية للمجموعة 💪

للبدء، يرجى اختيار طريقة إعداد المجموعة:
"""
    return send_message(chat_id, welcome_message, reply_markup=create_group_setup_keyboard())

def handle_group_help(chat_id):
    """معالجة أمر /grouphelp في المجموعة"""
    help_text = """
<b>مساعدة مجموعات بوت الدراسة والتحفيز</b> 📖

<b>أوامر المجموعات:</b>
/start - بدء البوت وإعداد المجموعة
/grouphelp - عرض هذه الرسالة
/morning - تفعيل الجدول الصباحي
/evening - تفعيل الجدول المسائي
/custom - إنشاء جدول مخصص
/motivation - إرسال رسالة تحفيزية
/ranking - عرض ترتيب المجموعة
/report - عرض تقرير المجموعة
/active - عرض المشاركين النشطين

<b>أوامر المعسكرات (للمشرفين فقط):</b>
/newcamp - إنشاء معسكر جديد
/addtask - إضافة مهمة لمعسكر
/campreport - عرض تقرير المعسكر

<b>للمساعدة الفردية:</b>
يمكنك التواصل مع البوت في الخاص للحصول على مساعدة مخصصة.
"""
    return send_message(chat_id, help_text)

def handle_group_message(message, user_id, chat_id, text, chat_type):
    """معالجة رسالة في المجموعة"""
    # تحديث معلومات المستخدم
    username = message.get("from", {}).get("username")
    first_name = message.get("from", {}).get("first_name")
    last_name = message.get("from", {}).get("last_name")
    
    # الحصول على المستخدم أو إنشاء مستخدم جديد
    user = User.get_or_create(
        telegram_id=user_id,
        username=username,
        first_name=first_name,
        last_name=last_name
    )

    # تحديث معلومات المجموعة
    from study_bot.models import Group, db
    # الحصول على اسم المجموعة
    group_title = message.get("chat", {}).get("title", f"مجموعة {chat_id}")
    
    # التحقق من وجود المجموعة أو إنشائها
    group = Group.query.filter_by(telegram_id=chat_id).first()
    if not group:
        group = Group(
            telegram_id=chat_id,
            title=group_title,
            is_active=True,
            admin_id=None  # سيتم تحديثه لاحقاً
        )
        db.session.add(group)
        db.session.commit()
        logger.info(f"تم إنشاء مجموعة جديدة: {group_title} ({chat_id})")
    
    # معالجة الأوامر
    if text and text.startswith('/'):
        # استخراج الأمر الأساسي (حذف @botname إن وجد)
        command_parts = text.split()[0].lower().split('@')
        command = command_parts[0].lower()
        bot_username = command_parts[1].lower() if len(command_parts) > 1 else None
        
        # التحقق مما إذا كان الأمر موجهًا لهذا البوت أو بدون تحديد بوت
        from study_bot.config import TELEGRAM_BOT_USERNAME
        if bot_username and bot_username != TELEGRAM_BOT_USERNAME.lower():
            # الأمر موجه لبوت آخر، تجاهله
            return
        
        # تقسيم النص للحصول على الأوامر والوسائط
        command_text = text.replace(command_parts[0], "", 1).strip()
        if bot_username:
            command_text = command_text.replace(f"@{bot_username}", "", 1).strip()
        
        # توجيه الأمر للمعالج المناسب
        if command == '/start':
            return handle_group_start(chat_id, user_id)
        elif command == '/grouphelp' or command == '/help':
            return handle_group_help(chat_id)
        elif command == '/schedule':
            from study_bot.bot.handlers.private import handle_schedule_command
            return handle_schedule_command(user_id, chat_id)
        elif command == '/points':
            from study_bot.bot.handlers.private import handle_points_command
            return handle_points_command(user_id, chat_id)
        elif command == '/motivation':
            from study_bot.bot.handlers.private import handle_motivation_command
            return handle_motivation_command(user_id, chat_id)
        elif command == '/settings':
            from study_bot.bot.handlers.private import handle_settings_command
            return handle_settings_command(user_id, chat_id)
        elif command == '/today':
            from study_bot.bot.handlers.private import handle_today_command
            return handle_today_command(user_id, chat_id)
        elif command == '/report':
            from study_bot.bot.handlers.private import handle_report_command
            return handle_report_command(user_id, chat_id)
        elif command == '/done':
            from study_bot.bot.handlers.private import handle_done_command
            return handle_done_command(user_id, chat_id, command_text.split())
        
        # أوامر المعسكرات (للمشرفين فقط)
        elif command == '/newcamp':
            from study_bot.custom_camps_handler import handle_create_camp_command
            result = handle_create_camp_command(group.id, user_id, command_text)
            return send_message(chat_id, result)
        elif command == '/addtask':
            from study_bot.custom_camps_handler import handle_add_camp_task_command
            result = handle_add_camp_task_command(group.id, user_id, command_text)
            return send_message(chat_id, result)
        elif command == '/campreport':
            from study_bot.custom_camps_handler import handle_camp_report_command
            result = handle_camp_report_command(group.id, user_id, command_text)
            return send_message(chat_id, result)
        
        # أوامر الجداول
        elif command == '/morning':
            message = "🌞 <b>جدول الصباح</b>\n\nلتفعيل الجدول الصباحي، يرجى استخدام زر التفعيل أدناه."
            keyboard = {
                "inline_keyboard": [
                    [{"text": "✅ تفعيل الجدول الصباحي", "callback_data": "group_confirm_morning"}]
                ]
            }
            return send_message(chat_id, message, reply_markup=keyboard)
        
        elif command == '/evening':
            message = "🌙 <b>جدول المساء</b>\n\nلتفعيل الجدول المسائي، يرجى استخدام زر التفعيل أدناه."
            keyboard = {
                "inline_keyboard": [
                    [{"text": "✅ تفعيل الجدول المسائي", "callback_data": "group_confirm_evening"}]
                ]
            }
            return send_message(chat_id, message, reply_markup=keyboard)
        
        elif command == '/custom':
            message = "🔧 <b>جدول مخصص</b>\n\nلإنشاء جدول مخصص، يرجى إرسال تفاصيل الجدول بالصيغة التالية:\n/custom وقت1 وقت2 وقت3..."
            keyboard = {
                "inline_keyboard": [
                    [{"text": "✅ إنشاء جدول مخصص", "callback_data": "group_schedule_custom"}]
                ]
            }
            return send_message(chat_id, message, reply_markup=keyboard)
        
        elif command == '/ranking':
            # عرض ترتيب المجموعة
            message = "🏆 <b>ترتيب المجموعة</b>\n\nجاري تطوير هذه الميزة..."
            return send_message(chat_id, message)
        
        elif command == '/active':
            # عرض المشاركين النشطين
            message = "👥 <b>المشاركون النشطون</b>\n\nجاري تطوير هذه الميزة..."
            return send_message(chat_id, message)
        
        else:
            # إذا لم يتم التعرف على الأمر، لا نرسل رسالة خطأ في المجموعة لتجنب الإزعاج
            # نسجل الأمر غير المعروف للتطوير المستقبلي
            logger.info(f"أمر غير معروف في المجموعة: {command} من المستخدم {user_id} في المجموعة {chat_id}")
            pass
