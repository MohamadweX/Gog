#!/usr/bin/env python3
"""
وحدة أوامر المشرفين
تحتوي على معالجة أوامر المشرفين في الدردشة الخاصة
"""

import json
import logging
from datetime import datetime, timedelta

from study_bot.config import logger
from study_bot.models import User, Group, db
from study_bot.camps_models import CustomCamp, CampTask, CampParticipant
from study_bot.bot import send_message
from study_bot.private_camp_manager import handle_admin_groups, handle_admin_camps

# تعريف قائمة المشرف
ADMIN_MENU = {
    'inline_keyboard': [
        [{'text': '👥 إدارة مجموعاتي', 'callback_data': 'admin_groups'}],
        [{'text': '🏝️ إدارة المعسكرات', 'callback_data': 'admin_camps'}],
        [{'text': '➕ إنشاء معسكر جديد', 'callback_data': 'create_new_camp'}],
        [{'text': '✍️ تخصيص معسكر', 'callback_data': 'customize_camp'}],
        [{'text': '📥 العودة للقائمة الرئيسية', 'callback_data': 'back_to_main'}]
    ]
}

# قاموس لتخزين حالة الإعداد
admin_setup_states = {}

def handle_groups_command(user_data):
    """معالجة أمر /groups"""
    chat_id = user_data['chat_id']
    user_id = user_data['user_id']
    
    # التحقق من أن المستخدم مشرف على مجموعة واحدة على الأقل
    admin_groups = Group.query.filter_by(admin_id=user_id).all()
    
    if not admin_groups:
        send_message(chat_id, "❗ أنت لست مشرفًا على أي مجموعة حاليًا. الرجاء إضافة البوت إلى مجموعة وتفعيله لتصبح مشرفًا.")
        return False
    
    return handle_admin_groups(user_id, chat_id)

def handle_camps_command(user_data):
    """معالجة أمر /camps"""
    chat_id = user_data['chat_id']
    user_id = user_data['user_id']
    
    # التحقق من أن المستخدم مشرف على مجموعة واحدة على الأقل
    admin_groups = Group.query.filter_by(admin_id=user_id).all()
    
    if not admin_groups:
        send_message(chat_id, "❗ أنت لست مشرفًا على أي مجموعة حاليًا. يجب أن تكون مشرفًا على مجموعة لإدارة المعسكرات.")
        return False
        
    # الحصول على قائمة بمعرفات المجموعات التي يشرف عليها المستخدم
    admin_group_ids = [group.id for group in admin_groups]
    
    # الحصول على قائمة المعسكرات النشطة لهذه المجموعات
    camps = CustomCamp.query.filter(
        CustomCamp.group_id.in_(admin_group_ids),
        CustomCamp.is_active == True
    ).all()
    
    # إنشاء لوحة مفاتيح الأزرار
    keyboard = []
    
    # إذا كانت هناك معسكرات، عرضها
    if camps:
        for camp in camps:
            group_name = Group.query.get(camp.group_id).title
            keyboard.append([{
                'text': f"{camp.name} (المجموعة: {group_name})",
                'callback_data': f"manage_camp:{camp.id}"
            }])
        
    # إضافة زر إنشاء معسكر جديد
    keyboard.append([{'text': '➕ إنشاء معسكر جديد', 'callback_data': 'create_new_camp'}])
    # إضافة زر العودة للقائمة الرئيسية
    keyboard.append([{'text': '🔙 رجوع للقائمة الرئيسية', 'callback_data': 'back_to_main'}])
    
    # إعداد الرسالة
    if camps:
        message = f"""🏝️ <b>إدارة المعسكرات الدراسية</b>
        
لديك {len(camps)} معسكر/معسكرات دراسية نشطة.
اختر معسكرًا لإدارته أو أنشئ معسكرًا جديدًا:
"""
    else:
        message = """🏝️ <b>لا توجد معسكرات دراسية نشطة</b>
            
لم يتم إنشاء أي معسكر دراسي بعد للمجموعات التي تشرف عليها.

يمكنك إنشاء معسكر جديد بالضغط على زر "إنشاء معسكر جديد" أدناه.
"""
    
    # إرسال الرسالة مع لوحة المفاتيح
    markup = {'inline_keyboard': keyboard}
    send_message(chat_id, message, markup)
    return True

def handle_newcamp_command(user_data):
    """معالجة أمر /newcamp"""
    chat_id = user_data['chat_id']
    user_id = user_data['user_id']
    
    # التحقق من أن المستخدم مشرف على مجموعة واحدة على الأقل
    admin_groups = Group.query.filter_by(admin_id=user_id).all()
    
    if not admin_groups:
        send_message(chat_id, "❗ أنت لست مشرفًا على أي مجموعة حاليًا. يجب أن تكون مشرفًا على مجموعة لإنشاء معسكر جديد.")
        return False
    
    # إنشاء قائمة بالمجموعات ليختار المستخدم من بينها
    groups_keyboard = []
    for group in admin_groups:
        groups_keyboard.append([{
            'text': group.title,
            'callback_data': f'new_camp_for_group:{group.id}'
        }])
    
    # إضافة زر الرجوع للقائمة الرئيسية
    groups_keyboard.append([{'text': '🔙 رجوع للقائمة الرئيسية', 'callback_data': 'back_to_main'}])
    
    # رسالة إنشاء معسكر جديد
    newcamp_message = """🏝️ <b>إنشاء معسكر دراسي جديد</b>

اختر المجموعة التي تريد إنشاء معسكر دراسي لها:
"""
    
    # إرسال رسالة إنشاء معسكر جديد
    markup = {'inline_keyboard': groups_keyboard}
    send_message(chat_id, newcamp_message, markup)
    return True

def handle_customcamp_command(user_data):
    """معالجة أمر /customcamp"""
    chat_id = user_data['chat_id']
    user_id = user_data['user_id']
    
    # التحقق من أن المستخدم مشرف على مجموعة واحدة على الأقل
    admin_groups = Group.query.filter_by(admin_id=user_id).all()
    
    if not admin_groups:
        send_message(chat_id, "❗ أنت لست مشرفًا على أي مجموعة حاليًا. يجب أن تكون مشرفًا على مجموعة لتخصيص معسكر.")
        return False
    
    # رسالة تخصيص معسكر
    customcamp_message = """✍️ <b>تخصيص معسكر دراسي</b>

يمكنك تخصيص معسكرك الدراسي بإضافة مهام وأنشطة جديدة مع تحديد مواعيد ونقاط لكل منها.

<b>لإضافة مهمة جديدة</b> استخدم الأمر:
<code>/add_camp_task رقم المعسكر | عنوان المهمة | وصف المهمة | وقت الجدولة YYYY-MM-DD HH:MM | النقاط | المهلة بالدقائق</code>

<b>مثال:</b>
<code>/add_camp_task 1 | مذاكرة الرياضيات | حل تمارين الفصل الثالث | 2025-05-15 19:00 | 10 | 60</code>

للاطلاع على قائمة المعسكرات الخاصة بمجموعاتك، استخدم الأمر <code>/camps</code>.
"""
    
    # إرسال رسالة تخصيص معسكر
    send_message(chat_id, customcamp_message)
    return True

def handle_grouphelp_command(user_data):
    """معالجة أمر /grouphelp"""
    chat_id = user_data['chat_id']
    
    # رسالة مساعدة المجموعات
    grouphelp_message = """📁 <b>دليل إدارة المجموعات والمعسكرات الدراسية</b>

<b>الأوامر الرئيسية:</b>

• <code>/groups</code> - عرض وإدارة المجموعات التي أنت مشرف عليها
• <code>/camps</code> - عرض وإدارة المعسكرات الدراسية
• <code>/newcamp</code> - إنشاء معسكر دراسي جديد
• <code>/customcamp</code> - تخصيص معسكر دراسي موجود

<b>إنشاء وإدارة المعسكرات:</b>

1. إنشاء معسكر جديد:
   <code>/create_camp اسم المعسكر | وصف | تاريخ البداية | تاريخ النهاية | الحد الأقصى</code>

2. إضافة مهمة لمعسكر:
   <code>/add_camp_task رقم المعسكر | عنوان | وصف | وقت | نقاط | مهلة</code>

3. عرض تقرير معسكر:
   <code>/camp_report رقم المعسكر</code>

<b>ملاحظات هامة:</b>

• يمكنك إدارة المجموعات والمعسكرات من المحادثة الخاصة مع البوت.
• سيتم إرسال المهام في المواعيد المحددة إلى المجموعة تلقائيًا.
• كل مهمة لها مهلة زمنية للمشاركة وحصد النقاط.
• يمكن للمشاركين فقط التفاعل مع مهام المعسكر.

للمساعدة في استخدام أي أمر، أرسل الأمر بدون معاملات لعرض التعليمات.
"""
    
    # إرسال رسالة المساعدة
    send_message(chat_id, grouphelp_message)
    return True

def handle_admin_callback_query(callback_data, user_data):
    """معالجة الاستجابات للأزرار في قائمة المشرف"""
    chat_id = user_data['chat_id']
    user_id = user_data['user_id']
    message_id = user_data.get('message_id')
    
    if callback_data == 'admin_groups':
        # عرض قائمة المجموعات
        return handle_admin_groups(user_id, chat_id, message_id)
    
    elif callback_data == 'admin_camps':
        # عرض قائمة المعسكرات
        return handle_admin_camps(user_id, chat_id, message_id)
    
    elif callback_data == 'create_new_camp':
        # إنشاء معسكر جديد
        return handle_newcamp_command({'chat_id': chat_id, 'user_id': user_id})
    
    elif callback_data == 'customize_camp':
        # تخصيص معسكر
        return handle_customcamp_command({'chat_id': chat_id, 'user_id': user_id})
    
    return False

def handle_admin_schedule_command(user_data):
    """معالجة أمر /schedule للمشرفين"""
    chat_id = user_data['chat_id']
    user_id = user_data['user_id']
    
    # التحقق من أن المستخدم مشرف على مجموعة واحدة على الأقل
    admin_groups = Group.query.filter_by(admin_id=user_id).all()
    
    if not admin_groups:
        # ليس مشرفًا، يتم معالجة الجدول الشخصي بدلاً من ذلك
        return False
    
    # عرض قائمة للاختيار بين الجدول الشخصي وجدول المجموعة
    schedule_options = {
        'inline_keyboard': [
            [{'text': '👤 جدولي الشخصي', 'callback_data': 'personal_schedule'}],
            [{'text': '👥 جدول مجموعة', 'callback_data': 'group_schedule_select'}],
            [{'text': '📥 العودة للقائمة الرئيسية', 'callback_data': 'back_to_main'}]
        ]
    }
    
    schedule_message = """📅 <b>إدارة الجداول</b>

أنت مشرف على مجموعة وبإمكانك إدارة نوعين من الجداول:

• <b>جدولك الشخصي:</b> لمتابعة مهامك وإنجازاتك الشخصية

• <b>جدول المجموعة:</b> لإدارة جدول المجموعة والمعسكرات الدراسية

اختر نوع الجدول الذي تريد إدارته:
"""
    
    send_message(chat_id, schedule_message, schedule_options)
    return True
