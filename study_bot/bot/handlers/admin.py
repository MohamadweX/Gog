#!/usr/bin/env python3
"""
معالج رسائل المشرفين
يحتوي على وظائف لمعالجة رسائل وأوامر المشرفين
"""

import json
from datetime import datetime

from study_bot.bot import send_message
from study_bot.models import User
from study_bot.config import logger

# قائمة معرفات المشرفين الرئيسيين
ADMIN_IDS = [123456789]  # يجب تغييرها إلى المعرفات الحقيقية

def is_admin(user_id):
    """التحقق مما إذا كان المستخدم مشرفًا"""
    return user_id in ADMIN_IDS

def create_admin_menu_keyboard():
    """إنشاء لوحة مفاتيح قائمة المشرف"""
    return {
        "inline_keyboard": [
            [
                {"text": "المجموعات 👥", "callback_data": "admin_groups"},
                {"text": "المعسكرات ⛺", "callback_data": "admin_camps"}
            ],
            [
                {"text": "الإحصائيات 📊", "callback_data": "admin_stats"},
                {"text": "الإعدادات ⚙️", "callback_data": "admin_settings"}
            ],
            [
                {"text": "إرسال إشعار 📢", "callback_data": "admin_broadcast"}
            ]
        ]
    }

def handle_admin_command(user_id, chat_id):
    """معالجة أمر /admin"""
    if not is_admin(user_id):
        return send_message(chat_id, "عذرًا، هذا الأمر متاح للمشرفين فقط.")
    
    return send_message(chat_id, "مرحباً بك في لوحة تحكم المشرف. اختر من القائمة أدناه:", reply_markup=create_admin_menu_keyboard())

def handle_broadcast_command(user_id, chat_id, message_text):
    """معالجة أمر /broadcast لإرسال رسالة جماعية"""
    if not is_admin(user_id):
        return send_message(chat_id, "عذرًا، هذا الأمر متاح للمشرفين فقط.")
    
    # استخراج نص الرسالة
    parts = message_text.split(' ', 1)
    if len(parts) < 2:
        return send_message(chat_id, "يرجى توفير نص للإرسال. الصيغة: /broadcast [الرسالة]")
    
    broadcast_text = parts[1].strip()
    
    # إرسال الرسالة لجميع المستخدمين النشطين
    users = User.query.filter_by(is_active=True).all()
    sent_count = 0
    failed_count = 0
    
    # إضافة علامة تدل على أنها رسالة من المشرف
    formatted_text = f"📢 <b>رسالة من المشرف:</b>\n\n{broadcast_text}"
    
    for user in users:
        try:
            result = send_message(user.telegram_id, formatted_text)
            if result and result.get("ok", False):
                sent_count += 1
            else:
                failed_count += 1
        except Exception as e:
            logger.error(f"خطأ في إرسال رسالة جماعية للمستخدم {user.telegram_id}: {e}")
            failed_count += 1
    
    return send_message(chat_id, f"تم إرسال الرسالة بنجاح إلى {sent_count} مستخدم. فشل الإرسال لـ {failed_count} مستخدم.")

def handle_stats_command(user_id, chat_id):
    """معالجة أمر /stats لعرض إحصائيات البوت"""
    if not is_admin(user_id):
        return send_message(chat_id, "عذرًا، هذا الأمر متاح للمشرفين فقط.")
    
    # جمع الإحصائيات
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    morning_users = User.query.filter_by(preferred_schedule='morning').count()
    evening_users = User.query.filter_by(preferred_schedule='evening').count()
    custom_users = User.query.filter_by(preferred_schedule='custom').count()
    
    # إنشاء نص الإحصائيات
    stats_text = f"""
<b>إحصائيات بوت الدراسة والتحفيز</b> 📊

<b>المستخدمون:</b>
- إجمالي المستخدمين: {total_users}
- المستخدمون النشطون: {active_users}

<b>الجداول:</b>
- مستخدمو الجدول الصباحي: {morning_users}
- مستخدمو الجدول المسائي: {evening_users}
- مستخدمو الجدول المخصص: {custom_users}

<b>الوقت الحالي:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    return send_message(chat_id, stats_text)

def handle_admin_message(message, user_id, chat_id, text):
    """معالجة رسائل المشرف"""
    # معالجة أوامر المشرف
    if not text or not text.startswith('/'):
        return None
    
    command = text.split()[0].lower()
    
    if command == '/admin':
        return handle_admin_command(user_id, chat_id)
    elif command == '/broadcast':
        return handle_broadcast_command(user_id, chat_id, text)
    elif command == '/stats':
        return handle_stats_command(user_id, chat_id)
    
    # إذا لم تتم معالجة الأمر كأمر مشرف، فسيتم إرجاع None للسماح بمعالجته كأمر عادي
    return None
