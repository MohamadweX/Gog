#!/usr/bin/env python3
"""
وحدة معالجة المجموعات
تحتوي على وظائف للتفاعل مع المجموعات
"""

import json
import requests
from datetime import datetime, timedelta

from study_bot.config import TELEGRAM_API_URL, logger, TELEGRAM_BOT_TOKEN
from study_bot.models import User, Group, GroupParticipant, GroupScheduleTracker, MotivationalMessage, db
from study_bot.group_menus import (
    GROUP_SETUP_LOCATION_MENU, GROUP_SETTINGS_MENU, GROUP_SCHEDULE_MENU,
    GROUP_CONFIRM_MORNING_MENU, GROUP_CONFIRM_EVENING_MENU, GROUP_CONFIRM_CUSTOM_MENU,
    MORNING_JOIN_MENU, EVENING_JOIN_MENU, CUSTOM_JOIN_MENU, OPEN_PRIVATE_SETUP_MENU
)

# إرسال رسالة
def send_group_message(chat_id, text, reply_markup=None, parse_mode='HTML'):
    """إرسال رسالة إلى مجموعة"""
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
            return result['result']
        else:
            logger.error(f"خطأ في إرسال الرسالة للمجموعة: {result}")
            return None
    except Exception as e:
        logger.error(f"استثناء عند إرسال الرسالة للمجموعة: {e}")
        return None

# تعديل رسالة
def edit_group_message(chat_id, message_id, text, reply_markup=None, parse_mode='HTML'):
    """تعديل رسالة موجودة في مجموعة"""
    url = f"{TELEGRAM_API_URL}/editMessageText"
    payload = {
        'chat_id': chat_id,
        'message_id': message_id,
        'text': text,
        'parse_mode': parse_mode
    }
    
    if reply_markup:
        payload['reply_markup'] = json.dumps(reply_markup)
    
    try:
        response = requests.post(url, json=payload)
        result = response.json()
        
        if response.status_code == 200 and result.get('ok'):
            return True
        else:
            logger.error(f"خطأ في تعديل الرسالة في المجموعة: {result}")
            return False
    except Exception as e:
        logger.error(f"استثناء عند تعديل الرسالة في المجموعة: {e}")
        return False

# الرد على استعلام callback
def answer_callback_query(query_id, text=None, show_alert=False):
    """الرد على استعلام callback"""
    url = f"{TELEGRAM_API_URL}/answerCallbackQuery"
    payload = {
        'callback_query_id': query_id
    }
    
    if text:
        payload['text'] = text
    
    payload['show_alert'] = show_alert
    
    try:
        response = requests.post(url, json=payload)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"استثناء عند الرد على استعلام callback: {e}")
        return False

# معالجة أمر /start في المجموعة
def handle_group_start(group_data):
    """معالجة أمر /start في المجموعة"""
    chat_id = group_data['chat_id']
    user_id = group_data['user_id']
    title = group_data.get('group_title', "Group")
    
    # إنشاء المجموعة أو الحصول عليها من قاعدة البيانات
    group = Group.get_or_create(
        telegram_id=chat_id,
        title=title
    )
    
    # جدولة رسالة تأكيد التفعيل بعد دقيقتين
    from flask import current_app
    from study_bot.notification_utils import schedule_confirmation_message, send_admin_private_message
    schedule_confirmation_message(current_app, chat_id, is_group=True)
    
    # التحقق من المشرف
    if group.admin_id is None:
        # حفظ مشرف المجموعة
        group.admin_id = user_id
        db.session.commit()
        
        # إرسال رسالة الترحيب
        welcome_message = f"""
مرحبًا بك في بوت الدراسة والتحفيز! 👋

تم تعيينك كمشرف لهذه المجموعة لإدارة الجداول الدراسية ونظام النقاط. ⚖️

من فضلك اختر مكان استكمال إعداد البوت:
"""
        
        send_group_message(chat_id, welcome_message, GROUP_SETUP_LOCATION_MENU)
        
        # إرسال رسالة للمشرف في الخاص
        send_admin_private_message(current_app, group.id, user_id)
    else:
        # التحقق من أن المستخدم هو المشرف
        if user_id != group.admin_id:
            send_group_message(chat_id, f"❗ أنت لست مشرف المجموعة المسجل. فقط المشرف يمكنه إدارة البوت.")
            return False
        
        # إذا كان الإعداد مكتمل
        if group.setup_complete:
            # عرض قائمة الإعدادات
            settings_message = f"""
إعدادات المجموعة 📝
يمكنك تعديل الإعدادات للمجموعة {title}:
"""
            send_group_message(chat_id, settings_message, GROUP_SETTINGS_MENU)
            
            # إرسال رسالة تذكير للمشرف في الخاص
            from study_bot.notification_utils import send_admin_private_message
            send_admin_private_message(group.id, group.admin_id)
        else:
            # إذا كان الإعداد غير مكتمل
            incomplete_setup_message = f"""
يبدو أن الإعداد غير مكتمل ❗

من فضلك اختر مكان استكمال إعداد البوت:
"""
            send_group_message(chat_id, incomplete_setup_message, GROUP_SETUP_LOCATION_MENU)
    
    return True

# معالجة استجابات الأزرار التفاعلية للمجموعات
def handle_group_callback(callback_data, group_data):
    """معالجة استجابة المستخدم للأزرار التفاعلية في المجموعات"""
    callback_query_id = group_data.get('callback_query_id')
    chat_id = group_data['chat_id']
    user_id = group_data['user_id']
    message_id = group_data.get('message_id')
    
    # الحصول على المجموعة من قاعدة البيانات
    group = Group.query.filter_by(telegram_id=chat_id).first()
    
    if not group:
        answer_callback_query(callback_query_id, "❗ حدث خطأ في العثور على بيانات المجموعة. الرجاء إرسال /start للبدء من جديد.")
        return False
    
    # معالجة طلبات الانضمام للمعسكرات
    if callback_data == 'join_morning_camp':
        return handle_join_morning_camp(group, user_id, chat_id, callback_query_id)
    elif callback_data == 'join_evening_camp':
        return handle_join_evening_camp(group, user_id, chat_id, callback_query_id)
    
    # التحقق من المشرف إذا كانت عملية إدارة
    if callback_data.startswith('group_') and not callback_data.startswith('group_join_') and not callback_data.startswith('task_join:') and user_id != group.admin_id:
        answer_callback_query(callback_query_id, "❗ هذه العملية متاحة فقط لمشرف المجموعة.", True)
        return False
    
    # معالجة الاستجابة حسب نوعها
    if callback_data == 'group_setup_here':
        # إكمال الإعدادات في المجموعة
        return handle_group_setup_here(group, chat_id, message_id, callback_query_id)
    elif callback_data == 'group_setup_private':
        # إكمال الإعدادات في الخاص
        return handle_group_setup_private(group, chat_id, user_id, message_id, callback_query_id)
    elif callback_data == 'group_toggle_motivation':
        # تفعيل/إيقاف الرسائل التحفيزية
        return handle_group_toggle_motivation(group, chat_id, message_id, callback_query_id)
    elif callback_data == 'group_send_motivation':
        # إرسال رسالة تحفيزية فورية
        return handle_group_send_motivation(group, chat_id, callback_query_id)
    elif callback_data == 'group_schedule_settings':
        # إعدادات الجدول
        return handle_group_schedule_settings(group, chat_id, message_id, callback_query_id)
    elif callback_data == 'group_schedule_morning':
        # اختيار الجدول الصباحي
        return handle_group_schedule_morning(group, chat_id, message_id, callback_query_id)
    elif callback_data == 'group_schedule_evening':
        # اختيار الجدول المسائي
        return handle_group_schedule_evening(group, chat_id, message_id, callback_query_id)
    elif callback_data == 'group_confirm_morning':
        # تأكيد تفعيل الجدول الصباحي
        return handle_group_confirm_morning(group, chat_id, message_id, callback_query_id)
    elif callback_data == 'group_confirm_evening':
        # تأكيد تفعيل الجدول المسائي
        return handle_group_confirm_evening(group, chat_id, message_id, callback_query_id)
    elif callback_data == 'join_morning_schedule':
        # الانضمام للجدول الصباحي
        return handle_join_morning_schedule(group, user_id, chat_id, callback_query_id)
    elif callback_data == 'join_evening_schedule':
        # الانضمام للجدول المسائي
        return handle_join_evening_schedule(group, user_id, chat_id, callback_query_id)
    elif callback_data == 'group_schedule_custom':
        # اختيار الجدول المخصص
        return handle_group_schedule_custom(group, chat_id, message_id, callback_query_id)
    elif callback_data == 'group_confirm_custom':
        # تأكيد تفعيل الجدول المخصص
        return handle_group_confirm_custom(group, chat_id, message_id, callback_query_id)
    elif callback_data == 'join_custom_schedule':
        # الانضمام للجدول المخصص
        return handle_join_custom_schedule(group, user_id, chat_id, callback_query_id)
    elif callback_data == 'back_to_group_settings':
        # العودة إلى إعدادات المجموعة
        return handle_back_to_group_settings(group, chat_id, message_id, callback_query_id)
    elif callback_data == 'back_to_group_schedule':
        # العودة إلى إعدادات الجدول
        return handle_group_schedule_settings(group, chat_id, message_id, callback_query_id)
    elif callback_data == 'group_schedule_reset':
        # إعادة تهيئة الجدول
        return handle_group_schedule_reset(group, chat_id, message_id, callback_query_id)
    
    # معالجة الانضمام للمهام
    elif callback_data.startswith('task_join:'):
        # استدعاء وحدة مهام المجموعة
        from study_bot.group_tasks import handle_task_join
        
        # تقسيم البيانات
        parts = callback_data.split(':') 
        if len(parts) == 3:
            # task_join:task_type:schedule_id
            task_type = parts[1]
            schedule_id = parts[2]
            
            # معالجة الانضمام للمهمة
            return handle_task_join(task_type, schedule_id, user_id, chat_id, callback_query_id)
        else:
            answer_callback_query(callback_query_id, "❌ صيغة خاطئة للمهمة")
            return False
            
    # إذا وصلنا إلى هنا، فالاستجابة غير معروفة
    answer_callback_query(callback_query_id, "❓ استجابة غير معروفة")
    return False

# وظائف معالجة الإعدادات في المجموعة
def handle_group_setup_here(group, chat_id, message_id, callback_query_id):
    """معالجة إكمال الإعدادات في المجموعة"""
    group.setup_in_progress = True
    group.setup_stage = 'group_settings'
    db.session.commit()
    
    settings_message = f"""
إعدادات المجموعة 📝

اختر الإعدادات التي تريد تعديلها:
"""
    
    edit_group_message(chat_id, message_id, settings_message, GROUP_SETTINGS_MENU)
    answer_callback_query(callback_query_id)
    return True

def handle_group_setup_private(group, chat_id, user_id, message_id, callback_query_id):
    """معالجة إكمال الإعدادات في الخاص"""
    group.setup_in_progress = True
    group.setup_stage = 'private_settings'
    db.session.commit()
    
    private_setup_message = f"""
يمكنك إكمال إعداد البوت في الخاص. اضغط على الزر أدناه:
"""
    
    edit_group_message(chat_id, message_id, private_setup_message, OPEN_PRIVATE_SETUP_MENU)
    answer_callback_query(callback_query_id)
    return True

def handle_group_toggle_motivation(group, chat_id, message_id, callback_query_id):
    """تفعيل/إيقاف الرسائل التحفيزية"""
    # تغيير حالة تفعيل الرسائل التحفيزية
    group.motivation_enabled = not group.motivation_enabled
    db.session.commit()
    
    status = "مفعلة ✅" if group.motivation_enabled else "معطلة ❌"
    
    message = f"""
تم تغيير حالة الرسائل التحفيزية بنجاح!

الحالة الحالية: {status}

اختر إعدادات أخرى لتعديلها:
"""
    
    edit_group_message(chat_id, message_id, message, GROUP_SETTINGS_MENU)
    answer_callback_query(callback_query_id, f"تم تغيير حالة الرسائل التحفيزية إلى: {status}")
    return True

def handle_group_send_motivation(group, chat_id, callback_query_id):
    """إرسال رسالة تحفيزية فورية للمجموعة"""
    from study_bot.models import MotivationalMessage
    
    # الحصول على رسالة تحفيزية عشوائية
    motivation_message = MotivationalMessage.get_random_message()
    
    # إرسال الرسالة التحفيزية
    formatted_message = f"""
✨ <b>رسالة تحفيزية:</b> ✨

{motivation_message}
"""
    
    send_group_message(chat_id, formatted_message)
    answer_callback_query(callback_query_id, "تم إرسال رسالة تحفيزية بنجاح!")
    return True

def handle_group_schedule_settings(group, chat_id, message_id, callback_query_id):
    """عرض إعدادات الجدول"""
    schedule_message = f"""
إعدادات الجدول 📅

اختر نوع الجدول الذي ترغب في تفعيله للمجموعة:

الجداول النشطة حالياً:
- الجدول الصباحي: {'✅' if group.morning_schedule_enabled else '❌'}
- الجدول المسائي: {'✅' if group.evening_schedule_enabled else '❌'}
- الجدول المخصص: {'✅' if group.custom_schedule_enabled else '❌'}
"""
    
    edit_group_message(chat_id, message_id, schedule_message, GROUP_SCHEDULE_MENU)
    answer_callback_query(callback_query_id)
    return True

def handle_group_schedule_morning(group, chat_id, message_id, callback_query_id):
    """عرض تفاصيل الجدول الصباحي"""
    morning_schedule_message = f"""
🌞 <b>الجدول الصباحي العام للتذكيرات اليومية:</b>

📚 03:00: 🚀 بدايه المعسكر!
🕋 04:25: 🕋 صلاة الفجر يا بطل!
🥗 08:00: ☕ فطار وراحة خفيفة
📚 08:30: 📕 العوده للمعسكر!
🥗 11:00: ⏸ استراحة سريعة ١٥ دقيقة
📚 11:15: ⚡ العوده للمعسكر!
🕋 12:51: 🕛 صلاة الظهر
📚 13:01: 📚 مذاكرة بعد الصلاة
🥗 14:00: 💤 وقت القيلولة / الراحة
🥗 15:30: ⏰ الاستيقاظ والعاوده للمعسكر!
🕋 16:28: 🕋 صلاة العصر
📚 16:38: 📖 نكمل مذاكرة تاني!
🕋 19:39: 🌇 صلاة المغرب
🕋 21:06: 🌙 صلاة العشاء
📚 21:30: 📊 تقييم يومك الدراسي

إجمالي النقاط اليومية للجدول الصباحي: 50 نقطة سوف يتم ترتيب المنضمين حسب النقاط في نهاية اليوم

هل ترغب في تفعيل هذا الجدول للمجموعة؟
"""
    
    edit_group_message(chat_id, message_id, morning_schedule_message, GROUP_CONFIRM_MORNING_MENU)
    answer_callback_query(callback_query_id)
    return True

def handle_group_schedule_evening(group, chat_id, message_id, callback_query_id):
    """عرض تفاصيل الجدول المسائي"""
    evening_schedule_message = f"""
🌙 <b>الجدول المسائي للتذكيرات الدراسية:</b>

📚 16:00: 🚀 بدايه المعسكر الساعه 4:00 العصر!
🥗 20:00: ☕تناول العشاء
📚 20:30: 📖 عودة للمذاكرة!
🕋 21:10: 🕋 صلاة العشاء
🙏 01:30: 🤲قيام الليل 
📚 04:05: 📊 تقييم يومك الليلي
🕋 04:25: 🕋 صلاة الفجر



إجمالي نقاط الجدول الليلي: 40 نقطة
سوف يتم ترتيب الاعضاء حسب بالنقاط في نهايه المعسكر

هل ترغب في تفعيل هذا الجدول للمجموعة؟
"""
    
    edit_group_message(chat_id, message_id, evening_schedule_message, GROUP_CONFIRM_EVENING_MENU)
    answer_callback_query(callback_query_id)
    return True

def handle_group_confirm_morning(group, chat_id, message_id, callback_query_id):
    """تأكيد تفعيل الجدول الصباحي"""
    # تفعيل الجدول الصباحي
    group.update_schedule_status('morning', True)
    
    # تحديث حالة الإعداد
    if not group.setup_complete:
        group.setup_complete = True
        group.setup_in_progress = False
        db.session.commit()
    
    # إنشاء متابعة جدول للمجموعة
    tracker = GroupScheduleTracker.get_or_create_for_today(group.id, 'morning')
    
    confirmation_message = f"""
✅ تم تفعيل الجدول الصباحي بنجاح!

سوف يتم إرسال رسالة الجدول الصباحي في الساعة 03:00 صباحًا يوميا.
توزيع النقاط كالتالي:
- إجمالي النقاط اليومية للجدول الصباحي: 50 نقطة

اختر ما تريد فعله الآن:
"""
    
    edit_group_message(chat_id, message_id, confirmation_message, GROUP_SETTINGS_MENU)
    answer_callback_query(callback_query_id, "✅ تم تفعيل الجدول الصباحي بنجاح!")
    return True

def handle_group_confirm_evening(group, chat_id, message_id, callback_query_id):
    """تأكيد تفعيل الجدول المسائي"""
    # تفعيل الجدول المسائي
    group.update_schedule_status('evening', True)
    
    # تحديث حالة الإعداد
    if not group.setup_complete:
        group.setup_complete = True
        group.setup_in_progress = False
        db.session.commit()
    
    # إنشاء متابعة جدول للمجموعة
    tracker = GroupScheduleTracker.get_or_create_for_today(group.id, 'evening')
    
    confirmation_message = f"""
✅ تم تفعيل الجدول المسائي بنجاح!

سوف يتم إرسال رسالة الجدول المسائي في الساعة 16:00 مساءً يوميا.
توزيع النقاط كالتالي:
- إجمالي نقاط الجدول الليلي: 40 نقطة

اختر ما تريد فعله الآن:
"""
    
    edit_group_message(chat_id, message_id, confirmation_message, GROUP_SETTINGS_MENU)
    answer_callback_query(callback_query_id, "✅ تم تفعيل الجدول المسائي بنجاح!")
    return True

def handle_join_morning_schedule(group, user_id, chat_id, callback_query_id):
    """معالجة انضمام المستخدم للجدول الصباحي"""
    # التحقق من أن الجدول الصباحي مفعل للمجموعة
    if not group.morning_schedule_enabled:
        answer_callback_query(callback_query_id, "❌ الجدول الصباحي غير مفعل لهذه المجموعة.", True)
        return False
    
    # التحقق من إمكانية الانضمام
    tracker = GroupScheduleTracker.get_or_create_for_today(group.id, 'morning')
    if not tracker.is_join_open():
        answer_callback_query(callback_query_id, "❌ انتهى وقت الانضمام للجدول الصباحي. يمكنك الانضمام غدا.", True)
        return False
    
    # الحصول على المستخدم من قاعدة البيانات أو إنشاءه
    user = User.query.filter_by(telegram_id=user_id).first()
    if not user:
        user = User.get_or_create(telegram_id=user_id)
    
    # الحصول على مشارك المجموعة أو إنشاءه
    participant = GroupParticipant.get_or_create(group.id, user.id)
    
    # تحديث حالة المشاركة
    participant.update_participation('morning', True)
    
    # إضافة نقاط الانضمام
    participant.update_points(5, 'morning')
    
    # زيادة عدد المشاركين
    tracker.update_participants_count()
    
    # إرسال رسالة تأكيد
    user_name = user.first_name or f"User{user.telegram_id}"
    confirmation_message = f"🌞 انضم <b>{user_name}</b> للجدول الصباحي اليوم (+5 نقاط) 💪"
    send_group_message(chat_id, confirmation_message)
    
    # إرسال تأكيد للمستخدم
    answer_callback_query(callback_query_id, "✅ تم تسجيل انضمامك للجدول الصباحي اليوم (+5 نقاط)")
    return True

def handle_join_morning_camp(group, user_id, chat_id, callback_query_id):
    """معالجة انضمام المستخدم للمعسكر الصباحي"""
    # التحقق من أن الجدول الصباحي مفعل للمجموعة
    if not group.morning_schedule_enabled:
        answer_callback_query(callback_query_id, "❌ المعسكر الصباحي غير مفعل لهذه المجموعة.", True)
        return False
    
    # إنشاء متابعة الجدول لليوم الحالي
    tracker = GroupScheduleTracker.get_or_create_for_today(group.id, 'morning')
    
    # الحصول على المستخدم من قاعدة البيانات أو إنشاءه
    user = User.query.filter_by(telegram_id=user_id).first()
    if not user:
        # إنشاء مستخدم جديد
        user = User(telegram_id=user_id)
        db.session.add(user)
        db.session.commit()
    
    # إنشاء أو الحصول على مشاركة المستخدم في المجموعة
    participant = GroupParticipant.get_or_create(group.id, user.id)
    
    # تحديث حالة المشاركة في الجدول الصباحي
    participant.update_participation('morning', True)
    
    # إضافة 5 نقاط للانضمام
    participant.update_points(5, 'morning')
    
    # زيادة عدد المشاركين
    tracker.update_participants_count()
    
    # إرسال رسالة تأكيد
    user_name = user.first_name or f"مستخدم{user.telegram_id}"
    confirmation_message = f"🌞 انضم <b>{user_name}</b> للمعسكر الصباحي اليوم (+5 نقاط) 💪"
    send_group_message(chat_id, confirmation_message)
    
    # إرسال تأكيد للمستخدم
    answer_callback_query(callback_query_id, "✅ تم تسجيل انضمامك للمعسكر الصباحي اليوم (+5 نقاط)")
    return True

def handle_join_evening_camp(group, user_id, chat_id, callback_query_id):
    """معالجة انضمام المستخدم للمعسكر المسائي"""
    # التحقق من أن الجدول المسائي مفعل للمجموعة
    if not group.evening_schedule_enabled:
        answer_callback_query(callback_query_id, "❌ المعسكر المسائي غير مفعل لهذه المجموعة.", True)
        return False
    
    # إنشاء متابعة الجدول لليوم الحالي
    tracker = GroupScheduleTracker.get_or_create_for_today(group.id, 'evening')
    
    # الحصول على المستخدم من قاعدة البيانات أو إنشاءه
    user = User.query.filter_by(telegram_id=user_id).first()
    if not user:
        # إنشاء مستخدم جديد
        user = User(telegram_id=user_id)
        db.session.add(user)
        db.session.commit()
    
    # إنشاء أو الحصول على مشاركة المستخدم في المجموعة
    participant = GroupParticipant.get_or_create(group.id, user.id)
    
    # تحديث حالة المشاركة في الجدول المسائي
    participant.update_participation('evening', True)
    
    # إضافة 5 نقاط للانضمام
    participant.update_points(5, 'evening')
    
    # زيادة عدد المشاركين
    tracker.update_participants_count()
    
    # إرسال رسالة تأكيد
    user_name = user.first_name or f"مستخدم{user.telegram_id}"
    confirmation_message = f"🌙 انضم <b>{user_name}</b> للمعسكر المسائي اليوم (+5 نقاط) 💪"
    send_group_message(chat_id, confirmation_message)
    
    # إرسال تأكيد للمستخدم
    answer_callback_query(callback_query_id, "✅ تم تسجيل انضمامك للمعسكر المسائي اليوم (+5 نقاط)")
    return True

def handle_join_evening_schedule(group, user_id, chat_id, callback_query_id):
    """معالجة انضمام المستخدم للجدول المسائي"""
    # التحقق من أن الجدول المسائي مفعل للمجموعة
    if not group.evening_schedule_enabled:
        answer_callback_query(callback_query_id, "❌ الجدول المسائي غير مفعل لهذه المجموعة.", True)
        return False
    
    # التحقق من إمكانية الانضمام
    tracker = GroupScheduleTracker.get_or_create_for_today(group.id, 'evening')
    if not tracker.is_join_open():
        answer_callback_query(callback_query_id, "❌ انتهى وقت الانضمام للجدول المسائي. يمكنك الانضمام غدا.", True)
        return False
    
    # الحصول على المستخدم من قاعدة البيانات أو إنشاءه
    user = User.query.filter_by(telegram_id=user_id).first()
    if not user:
        user = User.get_or_create(telegram_id=user_id)
    
    # الحصول على مشارك المجموعة أو إنشاءه
    participant = GroupParticipant.get_or_create(group.id, user.id)
    
    # تحديث حالة المشاركة
    participant.update_participation('evening', True)
    
    # إضافة نقاط الانضمام
    participant.update_points(5, 'evening')
    
    # زيادة عدد المشاركين
    tracker.update_participants_count()
    
    # إرسال رسالة تأكيد
    user_name = user.first_name or f"User{user.telegram_id}"
    confirmation_message = f"🌙 انضم <b>{user_name}</b> للجدول المسائي اليوم (+5 نقاط) 💪"
    send_group_message(chat_id, confirmation_message)
    
    # إرسال تأكيد للمستخدم
    answer_callback_query(callback_query_id, "✅ تم تسجيل انضمامك للجدول المسائي اليوم (+5 نقاط)")
    return True

def handle_group_schedule_custom(group, chat_id, message_id, callback_query_id):
    """عرض تفاصيل إنشاء الجدول المخصص"""
    custom_schedule_message = f"""
✏️ <b>إنشاء جدول مخصص للمجموعة:</b>

الجدول المخصص يتيح لك إنشاء مهام دراسية مخصصة مع مهل زمنية محددة، ويمكن للمستخدمين المشاركة والحصول على نقاط.

الميزات:
- إنشاء مهام مخصصة بأسماء وأوصاف مختارة
- تحديد مهلة زمنية للانضمام إلى كل مهمة
- تحديد نقاط مختلفة لكل مهمة
- متابعة نقاط المشاركين

بعد تفعيل الجدول المخصص، يمكنك إرسال مهام باستخدام الأمر: /custom_task

هل ترغب في تفعيل الجدول المخصص للمجموعة؟
"""
    
    edit_group_message(chat_id, message_id, custom_schedule_message, GROUP_CONFIRM_CUSTOM_MENU)
    answer_callback_query(callback_query_id)
    return True

def handle_group_confirm_custom(group, chat_id, message_id, callback_query_id):
    """تأكيد تفعيل الجدول المخصص"""
    # تفعيل الجدول المخصص
    group.update_schedule_status('custom', True)
    
    # تحديث حالة الإعداد
    if not group.setup_complete:
        group.setup_complete = True
        group.setup_in_progress = False
        db.session.commit()
    
    # إنشاء متابعة جدول للمجموعة
    tracker = GroupScheduleTracker.get_or_create_for_today(group.id, 'custom')
    
    confirmation_message = f"""
✅ تم تفعيل الجدول المخصص بنجاح!

يمكنك الآن إنشاء مهام مخصصة باستخدام الأوامر التالية:

/custom_task <عنوان المهمة> | <وصف المهمة> | <نوع المهمة> | <النقاط> | <المهلة بالدقائق>

مثال: /custom_task مهمة سريعة | قم بحل 10 مسائل | study | 5 | 15

اختر ما تريد فعله الآن:
"""
    
    edit_group_message(chat_id, message_id, confirmation_message, GROUP_SETTINGS_MENU)
    answer_callback_query(callback_query_id, "✅ تم تفعيل الجدول المخصص بنجاح!")
    return True

def handle_join_custom_schedule(group, user_id, chat_id, callback_query_id):
    """معالجة انضمام المستخدم للجدول المخصص"""
    # التحقق من أن الجدول المخصص مفعل للمجموعة
    if not group.custom_schedule_enabled:
        answer_callback_query(callback_query_id, "❌ الجدول المخصص غير مفعل لهذه المجموعة.", True)
        return False
    
    # التحقق من إمكانية الانضمام
    tracker = GroupScheduleTracker.get_or_create_for_today(group.id, 'custom')
    if not tracker.is_join_open():
        answer_callback_query(callback_query_id, "❌ انتهى وقت الانضمام للجدول المخصص. يمكنك الانضمام غدا.", True)
        return False
    
    # الحصول على المستخدم من قاعدة البيانات أو إنشاءه
    user = User.query.filter_by(telegram_id=user_id).first()
    if not user:
        user = User.get_or_create(telegram_id=user_id)
    
    # الحصول على مشارك المجموعة أو إنشاءه
    participant = GroupParticipant.get_or_create(group.id, user.id)
    
    # تحديث حالة المشاركة
    participant.update_participation('custom', True)
    
    # إضافة نقاط الانضمام
    participant.update_points(5, 'custom')
    
    # زيادة عدد المشاركين
    tracker.update_participants_count()
    
    # إرسال رسالة تأكيد
    user_name = user.first_name or f"User{user.telegram_id}"
    confirmation_message = f"✏️ انضم <b>{user_name}</b> للجدول المخصص اليوم (+5 نقاط) 💪"
    send_group_message(chat_id, confirmation_message)
    
    # إرسال تأكيد للمستخدم
    answer_callback_query(callback_query_id, "✅ تم تسجيل انضمامك للجدول المخصص اليوم (+5 نقاط)")
    return True

def handle_group_schedule_reset(group, chat_id, message_id, callback_query_id):
    """إعادة تهيئة الجدول"""
    # إيقاف جميع الجداول
    group.morning_schedule_enabled = False
    group.evening_schedule_enabled = False
    group.custom_schedule_enabled = False
    db.session.commit()
    
    # رسالة تأكيد
    status_morning = "✅" if group.morning_schedule_enabled else "❌"
    status_evening = "✅" if group.evening_schedule_enabled else "❌"
    status_custom = "✅" if group.custom_schedule_enabled else "❌"
    
    reset_message = f"""
⚠️ <b>تم إعادة تهيئة جداول المجموعة بنجاح!</b>

تم إيقاف جميع الجداول. يمكنك الآن تفعيل الجدول الذي ترغب فيه.

اختر نوع الجدول الذي ترغب في تفعيله للمجموعة:

الجداول النشطة حالياً:
- الجدول الصباحي: {status_morning}
- الجدول المسائي: {status_evening}
- الجدول المخصص: {status_custom}
"""
    
    edit_group_message(chat_id, message_id, reset_message, GROUP_SCHEDULE_MENU)
    answer_callback_query(callback_query_id, "✅ تم إعادة تهيئة الجداول بنجاح")
    return True

def handle_back_to_group_settings(group, chat_id, message_id, callback_query_id):
    """العودة إلى إعدادات المجموعة"""
    settings_message = f"""
إعدادات المجموعة 📝

اختر الإعدادات التي تريد تعديلها:
"""
    
    edit_group_message(chat_id, message_id, settings_message, GROUP_SETTINGS_MENU)
    answer_callback_query(callback_query_id)
    return True

# وظيفة إرسال رسالة الجدول الصباحي
def send_morning_schedule_message(group_id):
    """إرسال رسالة الجدول الصباحي للمجموعة"""
    group = Group.query.get(group_id)
    if not group or not group.morning_schedule_enabled:
        return False
    
    # إنشاء متابعة جدول جديدة لليوم
    tracker = GroupScheduleTracker.get_or_create_for_today(group_id, 'morning')
    
    # إرسال رسالة الجدول
    morning_message = f"""
🌞 <b>الجدول الصباحي لليوم {datetime.now().strftime('%Y-%m-%d')}</b>

📚 03:00: 🚀 خطة يومك الدراسي!
🕋 04:25: 🕋 صلاة الفجر يا بطل!
🥗 08:00: ☕ فطار وراحة خفيفة
📚 08:30: 📕 يلا نرجع ننجز!
🥗 11:00: ⏸ استراحة سريعة ١٥ دقيقة
📚 11:15: ⚡ رجعنا نذاكر تاني!
🕋 12:51: 🕛 صلاة الظهر
📚 13:01: 📚 مذاكرة بعد الصلاة
🥗 14:00: 💤 وقت القيلولة / الراحة
🥗 15:30: ⏰ يلا فوق!
🕋 16:28: 🕋 صلاة العصر
📚 16:38: 📖 نكمل مذاكرة تاني!
🕋 19:39: 🌇 صلاة المغرب
🕋 21:06: 🌙 صلاة العشاء
📚 21:30: 📊 تقييم يومك الدراسي

💪 اضغط على الزر أدناه للانضمام للجدول الصباحي لليوم (باب الانضمام مفتوح حتى الساعة 03:15 فقط)
"""
    
    result = send_group_message(group.telegram_id, morning_message, MORNING_JOIN_MENU)
    if result:
        # تعيين رسالة الانضمام ووقت انتهائها
        tracker.set_join_message(result['message_id'], 15)  # ينتهي بعد 15 دقيقة
        tracker.message_id = result['message_id']
        db.session.commit()
        return True
    
    return False

# وظيفة إرسال رسالة الجدول المسائي
def send_evening_schedule_message(group_id):
    """إرسال رسالة الجدول المسائي للمجموعة"""
    group = Group.query.get(group_id)
    if not group or not group.evening_schedule_enabled:
        return False
    
    # إنشاء متابعة جدول جديدة لليوم
    tracker = GroupScheduleTracker.get_or_create_for_today(group_id, 'evening')
    
    # إرسال رسالة الجدول
    evening_message = f"""
🌙 <b>الجدول المسائي لليوم {datetime.now().strftime('%Y-%m-%d')}</b>

📚 16:00: 🚀 الهدف الليلي الدراسي!
🥗 20:00: ☕تناول العشاء
📚 20:30: 📖 عودة للمذاكرة!
🕋 21:10: 🕋 صلاة العشاء
🙏 01:30: 🤲قيام الليل 
📚 04:05: 📊 تقييم يومك الليلي
🕋 04:25: 🕋 صلاة الفجر

🌙 اضغط على الزر أدناه للانضمام للجدول المسائي لليوم (باب الانضمام مفتوح حتى الساعة 16:30 فقط)
"""
    
    result = send_group_message(group.telegram_id, evening_message, EVENING_JOIN_MENU)
    if result:
        # تعيين رسالة الانضمام ووقت انتهائها
        tracker.set_join_message(result['message_id'], 30)  # ينتهي بعد 30 دقيقة
        tracker.message_id = result['message_id']
        db.session.commit()
        return True
    
    return False
