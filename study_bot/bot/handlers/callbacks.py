#!/usr/bin/env python3
"""
معالج استجابات الأزرار
يحتوي على وظائف لمعالجة استجابات المستخدمين للأزرار التفاعلية
"""

import json
import requests
import random
from datetime import datetime

from study_bot.bot import send_message
from study_bot.models import User, MotivationalMessage, db
from study_bot.config import logger, TELEGRAM_API_URL, TELEGRAM_BOT_TOKEN


# وظائف مساعدة
def get_schedule_type_text(schedule_type):
    """الحصول على النص العربي لنوع الجدول"""
    schedule_types = {
        'morning': 'صباحي 🌞',
        'evening': 'مسائي 🌙',
        'custom': 'مخصص 🔧',
        None: 'غير محدد ❓'
    }
    return schedule_types.get(schedule_type, 'غير محدد ❓')


def get_achievement_level(points):
    """الحصول على مستوى الإنجاز بناءً على النقاط"""
    if points < 50:
        return "مبتدئ 🌱"
    elif points < 100:
        return "نشيط 🔥"
    elif points < 200:
        return "متقدم 🌟"
    elif points < 500:
        return "محترف 🏆"
    elif points < 1000:
        return "خبير 🎓"
    else:
        return "أسطوري 👑"

# دالة تعديل الرسائل
def edit_message(chat_id, message_id, text, reply_markup=None, parse_mode='HTML'):
    """تعديل رسالة موجودة"""
    method = "editMessageText"
    url = f"{TELEGRAM_API_URL}/bot{TELEGRAM_BOT_TOKEN}/{method}"
    
    data = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": parse_mode
    }
    
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)
    
    try:
        logger.debug(f"تعديل رسالة: {url} مع البيانات: {json.dumps(data)}")
        response = requests.post(url, json=data, timeout=60)
        
        if response.status_code != 200:
            logger.error(f"فشل في تعديل الرسالة: {response.text}")
            return None
            
        return response.json().get("result")
    except Exception as e:
        logger.error(f"خطأ في تعديل الرسالة: {e}")
        return None
from study_bot.models import User, MotivationalMessage, db
from study_bot.config import logger, TELEGRAM_API_URL, TELEGRAM_BOT_TOKEN

# قائمة من العبارات التحفيزية المضمنة إذا لم يتم العثور على أي في قاعدة البيانات
MOTIVATIONAL_QUOTES = [
    "النجاح ليس نهائياً، والفشل ليس قاتلاً: إنما الشجاعة للاستمرار هي ما يهم.",
    "العلم يرفع بيتاً لا عماد له، والجهل يهدم بيت العز والكرم.",
    "الوقت كالسيف إن لم تقطعه قطعك.",
    "من طلب العلا سهر الليالي.",
    "من جد وجد، ومن زرع حصد.",
    "خير جليس في الزمان كتاب.",
    "العلم في الصغر كالنقش على الحجر.",
    "اطلبوا العلم من المهد إلى اللحد.",
    "إنما النصر صبر ساعة.",
    "ما ضاع حق وراءه مطالب."
]

def send_motivational_quote(user_id):
    """إرسال رسالة تحفيزية للمستخدم"""
    try:
        # الحصول على المستخدم من قاعدة البيانات
        user = User.query.filter_by(telegram_id=user_id).first()
        if not user:
            logger.error(f"لم يتم العثور على المستخدم {user_id}")
            return False
            
        # الحصول على رسالة تحفيزية عشوائية من قاعدة البيانات
        motivational_message = MotivationalMessage.query.order_by(db.func.random()).first()
        
        # إذا لم يتم العثور على رسائل في قاعدة البيانات، استخدم الرسائل المضمنة
        if not motivational_message:
            quote = random.choice(MOTIVATIONAL_QUOTES)
        else:
            quote = motivational_message.message
        
        # إنشاء رسالة تحفيزية كاملة
        motivation_text = f"""
✨ <b>رسالة تحفيزية:</b>

"{quote}"

🔥 استمر في التقدم! الإنجاز ينتظرك.
"""
        
        # إرسال الرسالة
        send_message(user.telegram_id, motivation_text)
        logger.info(f"تم إرسال رسالة تحفيزية للمستخدم {user_id}")
        return True
    except Exception as e:
        logger.error(f"خطأ في إرسال رسالة تحفيزية للمستخدم {user_id}: {e}")
        return False

def answer_callback_query(callback_query_id, text=None, show_alert=False):
    """الإجابة على نداء الاستجابة"""
    method = "answerCallbackQuery"
    # تأكد من تنسيق عنوان URL بشكل صحيح
    url = f"{TELEGRAM_API_URL}/bot{TELEGRAM_BOT_TOKEN}/{method}"
    
    data = {
        "callback_query_id": callback_query_id
    }
    
    if text:
        data["text"] = text
    
    data["show_alert"] = show_alert
    
    try:
        logger.debug(f"إرسال استجابة للازرار: {url} مع البيانات: {json.dumps(data)}")
        # استخدام json بدلاً من data لضمان ارسال البيانات بتنسيق JSON
        response = requests.post(url, json=data, timeout=60)
        if response.status_code != 200:
            logger.error(f"فشل في الإجابة على نداء الاستجابة: {response.text}")
        return response.json()
    except Exception as e:
        logger.error(f"خطأ في الإجابة على نداء الاستجابة: {e}")
        return None

def handle_private_callback(user_id, callback_data, message_id, chat_id, callback_query_id):
    """معالجة استجابة في الخاص"""
    # الحصول على المستخدم
    user = User.query.filter_by(telegram_id=user_id).first()
    if not user:
        answer_callback_query(callback_query_id, "خطأ: المستخدم غير مسجل.", True)
        return
    
    # استيراد الدوال المطلوبة هنا لتجنب الاستيراد الدائري
    from study_bot.bot.handlers.private import (
        handle_schedule_command, 
        handle_points_command, 
        handle_motivation_command, 
        handle_settings_command, 
        handle_help_command, 
        handle_today_command, 
        handle_report_command
    )
    
    # معالجة الاستجابات المختلفة
    if callback_data == "schedule":
        # عرض قائمة الجدول الدراسي
        answer_callback_query(callback_query_id, "جارٍ فتح الجدول الدراسي...")
        handle_schedule_command(user_id, chat_id)
    
    elif callback_data == "points":
        # عرض نقاط المستخدم
        answer_callback_query(callback_query_id, "جارٍ عرض نقاطك...")
        handle_points_command(user_id, chat_id)
    
    elif callback_data == "motivation":
        # عرض رسالة تحفيزية
        answer_callback_query(callback_query_id, "جارٍ إرسال رسالة تحفيزية...")
        handle_motivation_command(user_id, chat_id)
    
    elif callback_data == "settings":
        # عرض إعدادات المستخدم
        answer_callback_query(callback_query_id, "جارٍ فتح الإعدادات...")
        handle_settings_command(user_id, chat_id)
    
    elif callback_data == "help":
        # عرض مساعدة المستخدم
        answer_callback_query(callback_query_id, "جارٍ عرض المساعدة...")
        handle_help_command(user_id, chat_id)
        
    elif callback_data == "today":
        # عرض مهام اليوم
        answer_callback_query(callback_query_id, "جارٍ عرض مهام اليوم...")
        handle_today_command(user_id, chat_id)
        
    elif callback_data == "report":
        # عرض تقرير أداء المستخدم
        answer_callback_query(callback_query_id, "جارٍ عرض تقرير الأداء...")
        handle_report_command(user_id, chat_id)
        
    elif callback_data == "back_to_main" or callback_data == "main_menu":
        # العودة إلى القائمة الرئيسية
        answer_callback_query(callback_query_id, "جارٍ العودة إلى القائمة الرئيسية...")
        from study_bot.bot.handlers.private import show_main_menu
        show_main_menu(chat_id)
        
    elif callback_data.startswith("schedule_"):
        # معالجة الاستجابات المرتبطة بالجدول
        answer_callback_query(callback_query_id, "جارٍ معالجة طلب الجدول...")
        # استخراج نوع الجدول
        schedule_type = callback_data.split("_")[1]
        
        # تحديث تفضيلات المستخدم للجدول
        try:
            # الحصول على المستخدم من قاعدة البيانات
            user = User.query.filter_by(telegram_id=user_id).first()
            if user:
                # تحديث نوع الجدول المفضل للمستخدم
                user.preferred_schedule = schedule_type
                from study_bot.models import db
                db.session.commit()
                
                # إرسال رسالة تأكيد
                confirmation_message = f"""
✅ <b>تم تفعيل الجدول {schedule_type} بنجاح!</b>

• ستصلك تنبيهات الجدول حسب الأوقات المحددة
• تأكد من تفعيل الإشعارات لتلقي التنبيهات
• استخدم أمر /today لرؤية مهامك لليوم
                """
                send_message(chat_id, confirmation_message)
                
                # جدولة المهمة الأولى للمستخدم
                # يمكن إضافة وظيفة هنا لإرسال أول مهمة في الجدول المختار
                send_motivational_quote(user_id)
            else:
                send_message(chat_id, "❌ حدث خطأ: لم يتم العثور على المستخدم")
        except Exception as e:
            logger.error(f"خطأ في معالجة طلب تغيير الجدول: {e}")
            send_message(chat_id, f"❌ حدث خطأ أثناء تفعيل الجدول {schedule_type}")
        
    elif callback_data.startswith("settings_"):
        # معالجة الاستجابات المرتبطة بالإعدادات
        answer_callback_query(callback_query_id, "جارٍ معالجة طلب الإعدادات...")
        # استخراج نوع الإعداد
        settings_type = callback_data.split("_")[1]
        
        # تحديث إعدادات المستخدم
        try:
            # الحصول على المستخدم من قاعدة البيانات
            user = User.query.filter_by(telegram_id=user_id).first()
            if user:
                # معالجة أنواع مختلفة من الإعدادات
                if settings_type == "notifications":
                    # تبديل إعدادات الإشعارات
                    user.notifications_enabled = not user.notifications_enabled
                    from study_bot.models import db
                    db.session.commit()
                    
                    notification_status = "✅ مفعلة" if user.notifications_enabled else "❌ معطلة"
                    settings_message = f"""
✅ <b>تم تحديث الإعدادات</b>

<b>الإشعارات:</b> {notification_status}

استخدم الأزرار أدناه لتعديل الإعدادات الأخرى
"""
                    keyboard = {
                        "inline_keyboard": [
                            [
                                {"text": "تبديل إشعارات 🔔", "callback_data": "settings_notifications"}
                            ],
                            [
                                {"text": "تعديل الجدول ⏰", "callback_data": "settings_schedule"}
                            ],
                            [
                                {"text": "🔙 رجوع", "callback_data": "main_menu"}
                            ]
                        ]
                    }
                    send_message(chat_id, settings_message, reply_markup=keyboard)
                
                elif settings_type == "schedule":
                    # عرض إعدادات الجدول
                    handle_schedule_command(user_id, chat_id)
                
                elif settings_type == "profile":
                    # عرض الملف الشخصي
                    profile_message = f"""
👤 <b>الملف الشخصي</b>

<b>الاسم:</b> {user.get_full_name() or 'غير متوفر'}
<b>النقاط الكلية:</b> {user.total_points} نقطة
<b>نوع الجدول:</b> {get_schedule_type_text(user.preferred_schedule)}
<b>مستوى الإنجاز:</b> {get_achievement_level(user.total_points)}
<b>الإشعارات:</b> {'✅ مفعلة' if user.notifications_enabled else '❌ معطلة'}

• <i>استخدم أمر /points لعرض تفاصيل النقاط</i>
• <i>استخدم أمر /report لعرض تقرير الأداء</i>
"""
                    keyboard = {
                        "inline_keyboard": [
                            [
                                {"text": "تبديل إشعارات 🔔", "callback_data": "settings_notifications"}
                            ],
                            [
                                {"text": "🔙 رجوع", "callback_data": "main_menu"}
                            ]
                        ]
                    }
                    send_message(chat_id, profile_message, reply_markup=keyboard)
                else:
                    # إعدادات أخرى غير معروفة
                    settings_message = f"""
⚙️ <b>الإعدادات</b>

إعداد <b>{settings_type}</b> قيد التطوير وسيتم توفيره قريبًا.

اختر من الإعدادات المتاحة أدناه:
"""
                    keyboard = {
                        "inline_keyboard": [
                            [
                                {"text": "تبديل إشعارات 🔔", "callback_data": "settings_notifications"}
                            ],
                            [
                                {"text": "تعديل الجدول ⏰", "callback_data": "settings_schedule"}
                            ],
                            [
                                {"text": "الملف الشخصي 👤", "callback_data": "settings_profile"}
                            ],
                            [
                                {"text": "🔙 رجوع", "callback_data": "main_menu"}
                            ]
                        ]
                    }
                    send_message(chat_id, settings_message, reply_markup=keyboard)
            else:
                send_message(chat_id, "❌ حدث خطأ: لم يتم العثور على المستخدم")
        except Exception as e:
            logger.error(f"خطأ في معالجة طلب تغيير الإعدادات: {e}")
            send_message(chat_id, f"❌ حدث خطأ أثناء تعديل الإعدادات")
        
    # معالجة إعدادات المجموعة في الخاص
    elif callback_data.startswith("private_group_"):
        from study_bot.models import Group, db
        
        # فصل بيانات الاستجابة
        parts = callback_data.split(":")
        if len(parts) != 2:
            answer_callback_query(callback_query_id, "بيانات غير صالحة")
            return
            
        action = parts[0]
        group_id = int(parts[1])
        
        # التحقق من المجموعة
        group = Group.query.get(group_id)
        if not group or not group.is_active:
            answer_callback_query(callback_query_id, "المجموعة غير موجودة أو غير نشطة")
            return
            
        # التحقق من المشرف
        if group.admin_id != user_id:
            answer_callback_query(callback_query_id, "أنت لست مشرف هذه المجموعة")
            return
        
        # معالجة الإعدادات المختلفة
        if action == "private_group_morning":
            # إعدادات الجدول الصباحي
            answer_callback_query(callback_query_id, "جارٍ إعداد الجدول الصباحي...")
            
            morning_message = f"""
🌞 <b>الجدول الصباحي للمجموعة: {group.title}</b>

يتكون الجدول الصباحي من 15 مهمة موزعة على مدار اليوم من الساعة 3:00 صباحاً وحتى 21:30 مساءً.

<b>أوقات المهام:</b>
03:00, 05:00, 07:00, 08:30, 10:00, 11:30, 13:00, 14:30, 16:00, 17:00, 18:00, 19:00, 20:00, 21:00, 21:30

<b>الحالة:</b> {'✅ مفعّل' if group.morning_schedule_enabled else '❌ غير مفعّل'}

<b>لتفعيل أو تعطيل الجدول الصباحي، اضغط على الزر أدناه.</b>
"""
            keyboard = {
                "inline_keyboard": [
                    [{"text": f"{'✅ تعطيل' if group.morning_schedule_enabled else '✅ تفعيل'} الجدول الصباحي", "callback_data": f"private_toggle_morning:{group_id}"}],
                    [{"text": "🔙 رجوع للإعدادات", "callback_data": f"private_group_back:{group_id}"}]
                ]
            }
            
            send_message(chat_id, morning_message, reply_markup=keyboard)
            
        elif action == "private_group_evening":
            # إعدادات الجدول المسائي
            answer_callback_query(callback_query_id, "جارٍ إعداد الجدول المسائي...")
            
            evening_message = f"""
🌙 <b>الجدول المسائي للمجموعة: {group.title}</b>

يتكون الجدول المسائي من 8 مهام موزعة على المساء والليل من الساعة 16:00 مساءً وحتى 04:05 فجراً.

<b>أوقات المهام:</b>
16:00, 18:00, 20:00, 22:00, 00:00, 02:00, 03:30, 04:05

<b>الحالة:</b> {'✅ مفعّل' if group.evening_schedule_enabled else '❌ غير مفعّل'}

<b>لتفعيل أو تعطيل الجدول المسائي، اضغط على الزر أدناه.</b>
"""
            keyboard = {
                "inline_keyboard": [
                    [{"text": f"{'✅ تعطيل' if group.evening_schedule_enabled else '✅ تفعيل'} الجدول المسائي", "callback_data": f"private_toggle_evening:{group_id}"}],
                    [{"text": "🔙 رجوع للإعدادات", "callback_data": f"private_group_back:{group_id}"}]
                ]
            }
            
            send_message(chat_id, evening_message, reply_markup=keyboard)
            
        elif action == "private_group_motivation":
            # إعدادات الرسائل التحفيزية
            answer_callback_query(callback_query_id, "جارٍ إعداد الرسائل التحفيزية...")
            
            motivation_message = f"""
💪 <b>الرسائل التحفيزية للمجموعة: {group.title}</b>

الرسائل التحفيزية تساعد على رفع معنويات أعضاء المجموعة ودفعهم للاستمرار في الدراسة.

<b>الحالة:</b> {'✅ مفعّلة' if group.motivation_enabled else '❌ غير مفعّلة'}

<b>لتفعيل أو تعطيل الرسائل التحفيزية، اضغط على الزر أدناه.</b>
"""
            keyboard = {
                "inline_keyboard": [
                    [{"text": f"{'✅ تعطيل' if group.motivation_enabled else '✅ تفعيل'} الرسائل التحفيزية", "callback_data": f"private_toggle_motivation:{group_id}"}],
                    [{"text": "✉️ إرسال رسالة تحفيزية الآن", "callback_data": f"private_send_motivation:{group_id}"}],
                    [{"text": "🔙 رجوع للإعدادات", "callback_data": f"private_group_back:{group_id}"}]
                ]
            }
            
            send_message(chat_id, motivation_message, reply_markup=keyboard)
            
        elif action == "private_group_custom":
            # إعدادات الجدول المخصص
            answer_callback_query(callback_query_id, "جارٍ إعداد الجدول المخصص...")
            
            custom_message = f"""
🔧 <b>الجدول المخصص للمجموعة: {group.title}</b>

يمكنك إنشاء جدول مخصص للمجموعة بتحديد أوقات المهام التي تناسبكم.

<b>الحالة:</b> {'✅ مفعّل' if getattr(group, 'custom_schedule_enabled', False) else '❌ غير مفعّل'}

<b>لإنشاء جدول مخصص:</b>
1. ارسل رسالة للبوت في المجموعة باستخدام الأمر: <code>/custom</code> متبوعاً بقائمة الأوقات المطلوبة
2. مثال: <code>/custom 9:00 13:00 17:00 22:00</code>

<b>ملاحظات:</b>
- استخدم تنسيق 24 ساعة للوقت (مثل 14:30 بدلاً من 2:30 م)
- يمكنك إضافة حتى 10 أوقات مختلفة
"""
            keyboard = {
                "inline_keyboard": [
                    [{"text": "🔙 رجوع للإعدادات", "callback_data": f"private_group_back:{group_id}"}]
                ]
            }
            
            send_message(chat_id, custom_message, reply_markup=keyboard)
            
        elif action == "private_group_newcamp":
            # إنشاء معسكر جديد
            answer_callback_query(callback_query_id, "جارٍ إعداد معسكر جديد...")
            
            newcamp_message = f"""
🏕️ <b>إنشاء معسكر جديد للمجموعة: {group.title}</b>

المعسكرات هي فترات دراسية مكثفة مع مهام محددة ومواعيد دقيقة.

<b>لإنشاء معسكر جديد:</b>
1. اذهب إلى المجموعة واستخدم الأمر: <code>/newcamp</code> متبوعاً بتفاصيل المعسكر
2. مثال: <code>/newcamp اسم المعسكر | وصف المعسكر | 2025-06-01 | 2025-06-30 | 20</code>

<b>لإضافة مهام للمعسكر:</b>
1. بعد إنشاء المعسكر، استخدم الأمر: <code>/addtask</code> متبوعاً بتفاصيل المهمة
2. مثال: <code>/addtask 1 | مراجعة الفصل الأول | قراءة الصفحات 10-30 | 2025-06-01 10:00 | 5 | 30</code>

<b>لعرض تقرير المعسكر:</b>
- استخدم الأمر: <code>/campreport رقم_المعسكر</code>
"""
            keyboard = {
                "inline_keyboard": [
                    [{"text": "🔙 رجوع للإعدادات", "callback_data": f"private_group_back:{group_id}"}]
                ]
            }
            
            send_message(chat_id, newcamp_message, reply_markup=keyboard)
            
        elif action == "private_group_back":
            # العودة إلى قائمة إعدادات المجموعة
            answer_callback_query(callback_query_id, "جارٍ العودة إلى الإعدادات...")
            
            group_settings_message = f"""
<b>إعدادات المجموعة: {group.title}</b>

أنت مشرف لهذه المجموعة في بوت الدراسة والتحفيز. يمكنك إدارة الإعدادات التالية:

<b>الجدول الصباحي:</b> {'✅ مفعّل' if group.morning_schedule_enabled else '❌ غير مفعّل'}
<b>الجدول المسائي:</b> {'✅ مفعّل' if group.evening_schedule_enabled else '❌ غير مفعّل'}
<b>الرسائل التحفيزية:</b> {'✅ مفعّلة' if group.motivation_enabled else '❌ غير مفعّلة'}
<b>الجدول المخصص:</b> {'✅ مفعّل' if getattr(group, 'custom_schedule_enabled', False) else '❌ غير مفعّل'}
"""
            keyboard = {
                "inline_keyboard": [
                    [
                        {"text": "الجدول الصباحي 🌞", "callback_data": f"private_group_morning:{group.id}"},
                        {"text": "الجدول المسائي 🌙", "callback_data": f"private_group_evening:{group.id}"}
                    ],
                    [
                        {"text": "رسائل تحفيزية 💪", "callback_data": f"private_group_motivation:{group.id}"}
                    ],
                    [
                        {"text": "جدول مخصص 🔧", "callback_data": f"private_group_custom:{group.id}"}
                    ],
                    [
                        {"text": "إنشاء معسكر جديد 🏕️", "callback_data": f"private_group_newcamp:{group.id}"}
                    ],
                    [
                        {"text": "🔙 رجوع للقائمة الرئيسية", "callback_data": "main_menu"}
                    ]
                ]
            }
            
            send_message(chat_id, group_settings_message, reply_markup=keyboard)
    
    # معالجة إجراءات المجموعات في الخاص
    elif callback_data.startswith("private_toggle_") or callback_data.startswith("private_send_"):
        from study_bot.models import Group, db
        
        # فصل بيانات الاستجابة
        parts = callback_data.split(":")
        if len(parts) != 2:
            answer_callback_query(callback_query_id, "بيانات غير صالحة")
            return
            
        action = parts[0]
        group_id = int(parts[1])
        
        # التحقق من المجموعة
        group = Group.query.get(group_id)
        if not group or not group.is_active:
            answer_callback_query(callback_query_id, "المجموعة غير موجودة أو غير نشطة")
            return
            
        # التحقق من المشرف
        if group.admin_id != user_id:
            answer_callback_query(callback_query_id, "أنت لست مشرف هذه المجموعة")
            return
        
        # معالجة الإجراءات المختلفة
        if action == "private_toggle_morning":
            # تبديل حالة الجدول الصباحي
            group.morning_schedule_enabled = not group.morning_schedule_enabled
            db.session.commit()
            
            status = "تفعيل" if group.morning_schedule_enabled else "تعطيل"
            answer_callback_query(callback_query_id, f"تم {status} الجدول الصباحي", show_alert=True)
            
            # إعادة عرض إعدادات الجدول الصباحي
            callback_data = f"private_group_morning:{group_id}"
            handle_private_callback(user_id, callback_data, message_id, chat_id, callback_query_id)
            
        elif action == "private_toggle_evening":
            # تبديل حالة الجدول المسائي
            group.evening_schedule_enabled = not group.evening_schedule_enabled
            db.session.commit()
            
            status = "تفعيل" if group.evening_schedule_enabled else "تعطيل"
            answer_callback_query(callback_query_id, f"تم {status} الجدول المسائي", show_alert=True)
            
            # إعادة عرض إعدادات الجدول المسائي
            callback_data = f"private_group_evening:{group_id}"
            handle_private_callback(user_id, callback_data, message_id, chat_id, callback_query_id)
            
        elif action == "private_toggle_motivation":
            # تبديل حالة الرسائل التحفيزية
            group.motivation_enabled = not group.motivation_enabled
            db.session.commit()
            
            status = "تفعيل" if group.motivation_enabled else "تعطيل"
            answer_callback_query(callback_query_id, f"تم {status} الرسائل التحفيزية", show_alert=True)
            
            # إعادة عرض إعدادات الرسائل التحفيزية
            callback_data = f"private_group_motivation:{group_id}"
            handle_private_callback(user_id, callback_data, message_id, chat_id, callback_query_id)
            
        elif action == "private_send_motivation":
            # إرسال رسالة تحفيزية فورية
            from study_bot.group_tasks import send_motivational_quote
            
            # إرسال رسالة تحفيزية
            result = send_motivational_quote(group.id)
            
            if result:
                answer_callback_query(callback_query_id, "✅ تم إرسال رسالة تحفيزية للمجموعة!", show_alert=True)
            else:
                answer_callback_query(callback_query_id, "❌ حدث خطأ في إرسال الرسالة التحفيزية.", show_alert=True)
    
    else:
        # استجابة غير معروفة
        answer_callback_query(callback_query_id, f"استجابة غير معروفة ({callback_data})")

def handle_group_callback(user_id, callback_data, message_id, chat_id, callback_query_id):
    """معالجة استجابة في المجموعة"""
    # جلب المعلومات الضرورية
    from study_bot.models import Group, User, db
    
    # الحصول على المستخدم والمجموعة
    user = User.get_or_create(user_id)
    group = Group.query.filter_by(telegram_id=chat_id).first()
    
    if not group:
        # إنشاء مجموعة جديدة إذا لم تكن موجودة
        group = Group(
            telegram_id=chat_id,
            title=f"مجموعة {chat_id}",
            is_active=True,
            admin_id=None  # سيتم تحديثه لاحقًا
        )
        db.session.add(group)
        db.session.commit()
        logger.info(f"تم إنشاء مجموعة جديدة من خلال callback: {chat_id}")
    
    # الاستجابات الأساسية للمجموعة
    if callback_data == "group_setup_here":
        # إعداد المجموعة هنا
        answer_callback_query(callback_query_id, "جارٍ إعداد المجموعة...")
        
        # تحديث المجموعة لتعيين المستخدم الحالي كمشرف
        group.admin_id = user_id
        db.session.commit()
        
        # إنشاء رسالة الإعدادات
        setup_message = f"""
<b>تم إعداد المجموعة بنجاح! ✅</b>

<b>اسم المجموعة:</b> {group.title}
<b>المشرف:</b> {user.get_full_name()}

يمكنك الآن استخدام الميزات التالية:
- إنشاء وإدارة معسكرات دراسية (/newcamp)
- تفعيل جداول الدراسة (/morning, /evening, /custom)
- إرسال رسائل تحفيزية (/motivation)

للمزيد من المعلومات، استخدم /grouphelp
"""
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "الجدول الصباحي 🌞", "callback_data": "group_schedule_morning"},
                    {"text": "الجدول المسائي 🌙", "callback_data": "group_schedule_evening"}
                ],
                [
                    {"text": "رسائل تحفيزية 💪", "callback_data": "group_toggle_motivation"}
                ],
                [
                    {"text": "جدول مخصص 🔧", "callback_data": "group_schedule_custom"}
                ]
            ]
        }
        
        # تحديث الرسالة الحالية
        from study_bot.bot import edit_message
        edit_message(chat_id, message_id, setup_message, reply_markup=keyboard)
    
    elif callback_data == "group_setup_private":
        # إعداد المجموعة في الخاص
        answer_callback_query(callback_query_id, "يرجى الذهاب إلى الخاص لإعداد المجموعة.")
        
        # تحديث المجموعة لتعيين المستخدم الحالي كمشرف
        group.admin_id = user_id
        db.session.commit()
        
        # إرسال رسالة للمستخدم في الخاص
        group_settings_message = f"""
<b>إعدادات المجموعة: {group.title}</b>

أنت الآن مشرف لهذه المجموعة في بوت الدراسة والتحفيز. يمكنك إدارة الإعدادات التالية:
"""
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "الجدول الصباحي 🌞", "callback_data": f"private_group_morning:{group.id}"},
                    {"text": "الجدول المسائي 🌙", "callback_data": f"private_group_evening:{group.id}"}
                ],
                [
                    {"text": "رسائل تحفيزية 💪", "callback_data": f"private_group_motivation:{group.id}"}
                ],
                [
                    {"text": "جدول مخصص 🔧", "callback_data": f"private_group_custom:{group.id}"}
                ],
                [
                    {"text": "إنشاء معسكر جديد 🏕️", "callback_data": f"private_group_newcamp:{group.id}"}
                ]
            ]
        }
        
        send_message(user_id, group_settings_message, reply_markup=keyboard)
    
    # معالجة إعدادات الجدول الصباحي
    elif callback_data == "group_schedule_morning":
        answer_callback_query(callback_query_id, "عرض إعدادات الجدول الصباحي...")
        
        schedule_message = """
🌞 <b>الجدول الصباحي</b>

يتكون الجدول الصباحي من 15 مهمة موزعة على مدار اليوم من الساعة 3:00 صباحاً وحتى 21:30 مساءً.

<b>أوقات المهام:</b>
03:00, 05:00, 07:00, 08:30, 10:00, 11:30, 13:00, 14:30, 16:00, 17:00, 18:00, 19:00, 20:00, 21:00, 21:30

<b>لتفعيل الجدول الصباحي في المجموعة، اضغط على زر التفعيل أدناه.</b>
"""
        keyboard = {
            "inline_keyboard": [
                [{"text": "✅ تفعيل الجدول الصباحي", "callback_data": "group_confirm_morning"}],
                [{"text": "🔙 رجوع", "callback_data": "group_setup_here"}]
            ]
        }
        
        # تحديث الرسالة الحالية
        from study_bot.bot import edit_message
        edit_message(chat_id, message_id, schedule_message, reply_markup=keyboard)
    
    # معالجة إعدادات الجدول المسائي
    elif callback_data == "group_schedule_evening":
        answer_callback_query(callback_query_id, "عرض إعدادات الجدول المسائي...")
        
        schedule_message = """
🌙 <b>الجدول المسائي</b>

يتكون الجدول المسائي من 8 مهام موزعة على المساء والليل من الساعة 16:00 مساءً وحتى 04:05 فجراً.

<b>أوقات المهام:</b>
16:00, 18:00, 20:00, 22:00, 00:00, 02:00, 03:30, 04:05

<b>لتفعيل الجدول المسائي في المجموعة، اضغط على زر التفعيل أدناه.</b>
"""
        keyboard = {
            "inline_keyboard": [
                [{"text": "✅ تفعيل الجدول المسائي", "callback_data": "group_confirm_evening"}],
                [{"text": "🔙 رجوع", "callback_data": "group_setup_here"}]
            ]
        }
        
        # تحديث الرسالة الحالية
        from study_bot.bot import edit_message
        edit_message(chat_id, message_id, schedule_message, reply_markup=keyboard)
    
    # معالجة تفعيل الجدول الصباحي
    elif callback_data == "group_confirm_morning":
        answer_callback_query(callback_query_id, "جارٍ تفعيل الجدول الصباحي...")
        
        # تحديث إعدادات المجموعة
        group.morning_schedule_enabled = True
        db.session.commit()
        
        confirmation_message = """
✅ <b>تم تفعيل الجدول الصباحي بنجاح!</b>

سيتم إرسال تذكيرات المهام في الأوقات المحددة. يمكن للأعضاء الانضمام للجدول باستخدام الزر أدناه.

<b>الأعضاء:</b> اضغطوا على زر "انضمام للجدول الصباحي" للمشاركة والحصول على النقاط.
"""
        keyboard = {
            "inline_keyboard": [
                [{"text": "👤 انضمام للجدول الصباحي", "callback_data": "join_morning_schedule"}],
                [{"text": "🔙 رجوع للإعدادات", "callback_data": "group_setup_here"}]
            ]
        }
        
        # تحديث الرسالة الحالية
        from study_bot.bot import edit_message
        edit_message(chat_id, message_id, confirmation_message, reply_markup=keyboard)
    
    # معالجة تفعيل الجدول المسائي
    elif callback_data == "group_confirm_evening":
        answer_callback_query(callback_query_id, "جارٍ تفعيل الجدول المسائي...")
        
        # تحديث إعدادات المجموعة
        group.evening_schedule_enabled = True
        db.session.commit()
        
        confirmation_message = """
✅ <b>تم تفعيل الجدول المسائي بنجاح!</b>

سيتم إرسال تذكيرات المهام في الأوقات المحددة. يمكن للأعضاء الانضمام للجدول باستخدام الزر أدناه.

<b>الأعضاء:</b> اضغطوا على زر "انضمام للجدول المسائي" للمشاركة والحصول على النقاط.
"""
        keyboard = {
            "inline_keyboard": [
                [{"text": "👤 انضمام للجدول المسائي", "callback_data": "join_evening_schedule"}],
                [{"text": "🔙 رجوع للإعدادات", "callback_data": "group_setup_here"}]
            ]
        }
        
        # تحديث الرسالة الحالية
        from study_bot.bot import edit_message
        edit_message(chat_id, message_id, confirmation_message, reply_markup=keyboard)
    
    # معالجة الرسائل التحفيزية
    elif callback_data == "group_toggle_motivation":
        answer_callback_query(callback_query_id, "جارٍ تحديث إعدادات الرسائل التحفيزية...")
        
        # تبديل حالة الرسائل التحفيزية
        group.motivation_enabled = not group.motivation_enabled
        db.session.commit()
        
        status = "تفعيل" if group.motivation_enabled else "تعطيل"
        motivation_message = f"""
<b>تم {status} الرسائل التحفيزية!</b>

الحالة الحالية: {'✅ مفعّلة' if group.motivation_enabled else '❌ معطّلة'}

{'سيتم إرسال رسائل تحفيزية للمجموعة بشكل يومي.' if group.motivation_enabled else 'لن يتم إرسال رسائل تحفيزية للمجموعة.'}
"""
        keyboard = {
            "inline_keyboard": [
                [{"text": "🔄 تبديل الحالة", "callback_data": "group_toggle_motivation"}],
                [{"text": "✉️ إرسال رسالة تحفيزية الآن", "callback_data": "group_send_motivation"}],
                [{"text": "🔙 رجوع للإعدادات", "callback_data": "group_setup_here"}]
            ]
        }
        
        # تحديث الرسالة الحالية
        from study_bot.bot import edit_message
        edit_message(chat_id, message_id, motivation_message, reply_markup=keyboard)
    
    # معالجة إرسال رسالة تحفيزية فورية
    elif callback_data == "group_send_motivation":
        answer_callback_query(callback_query_id, "جارٍ إرسال رسالة تحفيزية...")
        
        # استيراد القائمة التحفيزية
        from study_bot.group_tasks import send_motivational_quote
        
        # إرسال رسالة تحفيزية
        send_motivational_quote(group.id)
        
        # إرسال تأكيد للمستخدم
        answer_callback_query(callback_query_id, "✅ تم إرسال رسالة تحفيزية للمجموعة!", show_alert=True)
    
    # معالجة انضمام المستخدم للجدول الصباحي
    elif callback_data == "join_morning_schedule":
        from study_bot.group_tasks import add_user_to_schedule
        
        result = add_user_to_schedule(group.id, user.id, "morning")
        
        if result:
            answer_callback_query(callback_query_id, "✅ تم انضمامك بنجاح للجدول الصباحي!", show_alert=True)
        else:
            answer_callback_query(callback_query_id, "❌ حدث خطأ في الانضمام للجدول الصباحي.", show_alert=True)
    
    # معالجة انضمام المستخدم للجدول المسائي
    elif callback_data == "join_evening_schedule":
        from study_bot.group_tasks import add_user_to_schedule
        
        result = add_user_to_schedule(group.id, user.id, "evening")
        
        if result:
            answer_callback_query(callback_query_id, "✅ تم انضمامك بنجاح للجدول المسائي!", show_alert=True)
        else:
            answer_callback_query(callback_query_id, "❌ حدث خطأ في الانضمام للجدول المسائي.", show_alert=True)
    
    # معالجة الجدول المخصص
    elif callback_data == "group_schedule_custom":
        answer_callback_query(callback_query_id, "عرض إعدادات الجدول المخصص...")
        
        custom_message = """
🔧 <b>الجدول المخصص</b>

يمكنك إنشاء جدول مخصص للمجموعة بتحديد أوقات المهام التي تناسبكم.

<b>لإنشاء جدول مخصص:</b>
1. استخدم الأمر: <code>/custom</code> متبوعاً بقائمة الأوقات المطلوبة
2. مثال: <code>/custom 9:00 13:00 17:00 22:00</code>

<b>ملاحظات:</b>
- استخدم تنسيق 24 ساعة للوقت (مثل 14:30 بدلاً من 2:30 م)
- يمكنك إضافة حتى 10 أوقات مختلفة
"""
        keyboard = {
            "inline_keyboard": [
                [{"text": "🔙 رجوع للإعدادات", "callback_data": "group_setup_here"}]
            ]
        }
        
        # تحديث الرسالة الحالية
        from study_bot.bot import edit_message
        edit_message(chat_id, message_id, custom_message, reply_markup=keyboard)
        
    # معالجة استجابات المعسكرات
    elif callback_data.startswith("camp_join:") or callback_data.startswith("camp_task_join:"):
        # استيراد معالج المعسكرات
        from study_bot.custom_camps_handler import handle_camp_callback_query
        # تمرير الاستجابة إلى معالج المعسكرات
        handle_camp_callback_query(callback_data, user_id, callback_query_id)
        
    elif callback_data == "camp_full":
        # استجابة للمعسكر الممتلئ
        answer_callback_query(callback_query_id, "⛔ المعسكر ممتلئ بالفعل وغير متاح للانضمام حالياً.")
    
    else:
        # استجابة غير معروفة
        logger.warning(f"استجابة غير معروفة في المجموعة: {callback_data} من المستخدم {user_id}")
        answer_callback_query(callback_query_id, f"استجابة غير معروفة: {callback_data}")
        

def handle_callback_query(callback_query):
    """معالجة استجابة المستخدم للأزرار التفاعلية"""
    # استخراج البيانات من الاستجابة
    callback_query_id = callback_query.get("id")
    user_id = callback_query.get("from", {}).get("id")
    message = callback_query.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    message_id = message.get("message_id")
    callback_data = callback_query.get("data")
    
    if not callback_query_id or not user_id or not chat_id or not message_id or not callback_data:
        logger.error(f"بيانات الاستجابة غير كاملة: {callback_query}")
        return
    
    # التحقق من نوع المحادثة
    chat_type = message.get("chat", {}).get("type", "private")
    
    if chat_type == "private":
        # معالجة استجابة في الخاص
        handle_private_callback(user_id, callback_data, message_id, chat_id, callback_query_id)
    else:
        # معالجة استجابة في المجموعة
        handle_group_callback(user_id, callback_data, message_id, chat_id, callback_query_id)
