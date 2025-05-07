#!/usr/bin/env python3
"""
قوائم البوت للمجموعات
يحتوي على تعريفات القوائم التفاعلية المستخدمة في المجموعات
"""

# قائمة اختيار مكان إعداد البوت
GROUP_SETUP_LOCATION_MENU = {
    'inline_keyboard': [
        [{'text': '⚙️ إكمال الإعدادات في المجموعة', 'callback_data': 'group_setup_here'}],
        [{'text': '📣 إكمال الإعدادات في الخاص', 'callback_data': 'group_setup_private'}]
    ]
}

# قائمة إعدادات المجموعة
GROUP_SETTINGS_MENU = {
    'inline_keyboard': [
        [{'text': '✨ تفعيل/إيقاف الرسائل التحفيزية', 'callback_data': 'group_toggle_motivation'}],
        [{'text': '📣 إرسال رسالة تحفيزية فورية', 'callback_data': 'group_send_motivation'}],
        [{'text': '📅 تفعيل الجدول الكامل', 'callback_data': 'group_schedule_settings'}]
    ]
}

# قائمة إعدادات جدول المجموعة
GROUP_SCHEDULE_MENU = {
    'inline_keyboard': [
        [{'text': '🌞 جدول صباحي', 'callback_data': 'group_schedule_morning'}],
        [{'text': '🌙 جدول مسائي', 'callback_data': 'group_schedule_evening'}],
        [{'text': '✏️ معسكر مخصص', 'callback_data': 'group_schedule_custom'}],
        [{'text': '🔄 إعادة تهيئة الجدول', 'callback_data': 'group_schedule_reset'}],
        [{'text': '🔙 رجوع', 'callback_data': 'back_to_group_settings'}]
    ]
}

# قائمة تأكيد تفعيل الجدول الصباحي
GROUP_CONFIRM_MORNING_MENU = {
    'inline_keyboard': [
        [{'text': '✅ تأكيد تفعيل الجدول الصباحي', 'callback_data': 'group_confirm_morning'}],
        [{'text': '🔙 رجوع', 'callback_data': 'back_to_group_schedule'}]
    ]
}

# قائمة تأكيد تفعيل الجدول المسائي
GROUP_CONFIRM_EVENING_MENU = {
    'inline_keyboard': [
        [{'text': '✅ تأكيد تفعيل الجدول المسائي', 'callback_data': 'group_confirm_evening'}],
        [{'text': '🔙 رجوع', 'callback_data': 'back_to_group_schedule'}]
    ]
}

# قائمة تأكيد تفعيل المعسكر المخصص
GROUP_CONFIRM_CUSTOM_MENU = {
    'inline_keyboard': [
        [{'text': '✅ تأكيد تفعيل المعسكر المخصص', 'callback_data': 'group_confirm_custom'}],
        [{'text': '🔙 رجوع', 'callback_data': 'back_to_group_schedule'}]
    ]
}

# قائمة الانضمام للجدول الصباحي
MORNING_JOIN_MENU = {
    'inline_keyboard': [
        [{'text': '💪 أنا معاكم النهارده!', 'callback_data': 'join_morning_schedule'}]
    ]
}

# قائمة الانضمام للجدول المسائي
EVENING_JOIN_MENU = {
    'inline_keyboard': [
        [{'text': '🌙 هشارك في الجدول الليلي', 'callback_data': 'join_evening_schedule'}]
    ]
}

# قائمة الانضمام للمعسكر المخصص
CUSTOM_JOIN_MENU = {
    'inline_keyboard': [
        [{'text': '✏️ هشارك في المعسكر المخصص', 'callback_data': 'join_custom_schedule'}]
    ]
}

# قائمة زر فتح إعدادات البوت في الخاص
OPEN_PRIVATE_SETUP_MENU = {
    'inline_keyboard': [
        [{'text': '⚙️ فتح إعدادات البوت في الخاص', 'callback_data': 'open_private_setup', 'url': 'https://t.me/Study_schedule501_bot?start=setup_group'}]
    ]
}
