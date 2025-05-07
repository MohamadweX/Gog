"""
وحدة معالجة المجموعات
تحتوي على وظائف للتفاعل مع المجموعات
"""

import json
import requests
import threading
import traceback
from datetime import datetime, timedelta

from study_bot.config import TELEGRAM_API_URL, logger, TELEGRAM_BOT_TOKEN
from study_bot.models import db

# قفل للتحكم في حالة الاتصال
_connection_lock = threading.Lock()

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
        with _connection_lock:
            response = requests.post(url, json=payload)
            result = response.json()
            
            if response.status_code == 200 and result.get('ok'):
                # زيادة عدد الرسائل المرسلة في الإحصائيات
                from study_bot.models import SystemStat
                SystemStat.increment('messages_sent')
                return result['result']
            else:
                error_message = result.get('description', 'Unknown error')
                logger.error(f"خطأ في إرسال الرسالة للمجموعة: {error_message}")
                
                # التحقق من أخطاء تيليجرام المعروفة
                if 'chat not found' in error_message.lower():
                    logger.warning(f"المجموعة {chat_id} غير موجودة أو لم يتم العثور عليها")
                elif 'bot was blocked by the user' in error_message.lower():
                    logger.warning(f"تم حظر البوت من قبل المستخدم")
                elif 'bot was kicked from the group' in error_message.lower():
                    logger.warning(f"تم طرد البوت من المجموعة {chat_id}")
                    # تحديث حالة المجموعة في قاعدة البيانات
                    from study_bot.models import Group
                    group = Group.query.filter_by(telegram_id=chat_id).first()
                    if group:
                        group.is_active = False
                        db.session.commit()
                
                return None
    except Exception as e:
        logger.error(f"استثناء عند إرسال الرسالة للمجموعة: {e}")
        logger.error(traceback.format_exc())
        return None


# تعديل رسالة
def edit_group_message(chat_id, message_id, text, reply_markup=None, parse_mode='HTML'):
    """تعديل رسالة موجودة في مجموعة"""
    try:
        # استدعاء الدالة المركزية لتعديل الرسائل
        from study_bot.bot import edit_message
        
        result = edit_message(chat_id, message_id, text, reply_markup, parse_mode)
        if result:
            return True
        else:
            logger.error(f"فشل في تعديل الرسالة في المجموعة")
            return False
    except Exception as e:
        logger.error(f"استثناء عند تعديل الرسالة في المجموعة: {e}")
        logger.error(traceback.format_exc())
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
        with _connection_lock:
            response = requests.post(url, json=payload)
            result = response.json()
            
            if response.status_code == 200 and result.get('ok'):
                return True
            else:
                logger.error(f"خطأ في الرد على استعلام callback: {result}")
                return False
    except Exception as e:
        logger.error(f"استثناء عند الرد على استعلام callback: {e}")
        logger.error(traceback.format_exc())
        return False


def handle_group_start(group_data):
    """معالجة أمر /start في المجموعة"""
    chat_id = group_data['chat_id']
    user_id = group_data['user_id']
    title = group_data.get('group_title', "Group")
    
    try:
        from study_bot.models import Group, User
        
        # إنشاء المجموعة أو الحصول عليها من قاعدة البيانات
        group = Group.get_or_create(
            telegram_id=chat_id,
            title=title
        )
        
        # جدولة رسالة تأكيد التفعيل بعد دقيقتين
        from study_bot.notification_utils import schedule_confirmation_message
        schedule_confirmation_message(chat_id, is_group=True, user_id=user_id)
        
        # التحقق من المشرف
        if group.admin_id is None:
            # حفظ مشرف المجموعة
            group.admin_id = user_id
            db.session.commit()
            logger.info(f"تم تعيين المستخدم {user_id} كمشرف للمجموعة {chat_id}")
        
        # إرسال رسالة الترحيب والإعدادات
        welcome_message = f"""👋 <b>مرحباً بك في بوت الدراسة والتحفيز!</b>

تم تفعيل البوت في مجموعة "{title}" بنجاح.

هذا البوت يساعد على تنظيم وقت المذاكرة والدراسة عبر:
• جداول دراسية يومية (صباحية أو مسائية)
• معسكرات دراسية مخصصة
• رسائل تحفيزية ودعم متواصل
• نظام نقاط لتشجيع المشاركة

<b>كيف تبدأ؟</b>
اختر طريقة الإعداد المناسبة لك:
"""
        
        # إضافة أزرار الإعداد
        from study_bot.group_menus import GROUP_SETUP_LOCATION_MENU
        
        # إرسال الرسالة
        send_group_message(chat_id, welcome_message, GROUP_SETUP_LOCATION_MENU)
        
        return True
    except Exception as e:
        logger.error(f"خطأ في معالجة أمر /start في المجموعة: {e}")
        logger.error(traceback.format_exc())
        return False


def handle_group_callback(callback_data, group_data):
    """معالجة استجابة المستخدم للأزرار التفاعلية في المجموعات"""
    try:
        chat_id = group_data['chat_id']
        user_id = group_data['user_id']
        message_id = group_data.get('message_id')
        callback_query_id = group_data.get('callback_query_id')
        
        from study_bot.models import Group, User
        
        # الحصول على المجموعة
        group = Group.query.filter_by(telegram_id=chat_id).first()
        if not group:
            logger.error(f"لم يتم العثور على المجموعة {chat_id} في قاعدة البيانات")
            answer_callback_query(callback_query_id, "❌ خطأ: لم يتم العثور على المجموعة", True)
            return False
        
        # التحقق من نوع الاستجابة
        if callback_data == 'group_setup_here':
            return handle_group_setup_here(group, chat_id, message_id, callback_query_id)
        elif callback_data == 'group_setup_private':
            return handle_group_setup_private(group, chat_id, user_id, message_id, callback_query_id)
        elif callback_data == 'group_toggle_motivation':
            return handle_group_toggle_motivation(group, chat_id, message_id, callback_query_id)
        elif callback_data == 'group_send_motivation':
            return handle_group_send_motivation(group, chat_id, callback_query_id)
        elif callback_data == 'group_schedule_settings':
            return handle_group_schedule_settings(group, chat_id, message_id, callback_query_id)
        elif callback_data == 'group_schedule_morning':
            return handle_group_schedule_morning(group, chat_id, message_id, callback_query_id)
        elif callback_data == 'group_schedule_evening':
            return handle_group_schedule_evening(group, chat_id, message_id, callback_query_id)
        elif callback_data == 'group_confirm_morning':
            return handle_group_confirm_morning(group, chat_id, message_id, callback_query_id)
        elif callback_data == 'group_confirm_evening':
            return handle_group_confirm_evening(group, chat_id, message_id, callback_query_id)
        elif callback_data == 'join_morning_schedule':
            return handle_join_morning_schedule(group, user_id, chat_id, callback_query_id)
        elif callback_data == 'join_evening_schedule':
            return handle_join_evening_schedule(group, user_id, chat_id, callback_query_id)
        elif callback_data == 'group_schedule_custom':
            return handle_group_schedule_custom(group, chat_id, message_id, callback_query_id)
        elif callback_data == 'group_confirm_custom':
            return handle_group_confirm_custom(group, chat_id, message_id, callback_query_id)
        elif callback_data == 'join_custom_schedule':
            return handle_join_custom_schedule(group, user_id, chat_id, callback_query_id)
        elif callback_data == 'group_schedule_reset':
            return handle_group_schedule_reset(group, chat_id, message_id, callback_query_id)
        elif callback_data == 'back_to_group_settings':
            return handle_back_to_group_settings(group, chat_id, message_id, callback_query_id)
        elif callback_data == 'back_to_group_schedule':
            return handle_group_schedule_settings(group, chat_id, message_id, callback_query_id)
        # معالجة مهام الجدول الصباحي
        elif callback_data.startswith('morning_task:'):
            task_name = callback_data.split(':')[1]
            from study_bot.group_tasks import handle_morning_task_completion
            return handle_morning_task_completion(group.id, user_id, task_name, callback_query_id)
        # معالجة مهام الجدول المسائي
        elif callback_data.startswith('evening_task:'):
            task_name = callback_data.split(':')[1]
            from study_bot.group_tasks import handle_evening_task_completion
            return handle_evening_task_completion(group.id, user_id, task_name, callback_query_id)
        # معالجة مهام المعسكر المخصص
        elif callback_data.startswith('join_camp:'):
            camp_id = int(callback_data.split(':')[1])
            from study_bot.custom_camps import handle_camp_join
            return handle_camp_join(camp_id, user_id, callback_query_id)
        elif callback_data.startswith('complete_camp_task:'):
            task_id = int(callback_data.split(':')[1])
            from study_bot.custom_camps import handle_camp_task_join
            return handle_camp_task_join(task_id, user_id, callback_query_id)
        else:
            logger.warning(f"استجابة غير معروفة: {callback_data}")
            answer_callback_query(callback_query_id, "⚠️ خيار غير مدعوم", True)
            return False
    except Exception as e:
        logger.error(f"خطأ في معالجة استجابة المستخدم في المجموعة: {e}")
        logger.error(traceback.format_exc())
        answer_callback_query(callback_query_id, "❌ حدث خطأ أثناء معالجة طلبك", True)
        return False


def handle_group_setup_here(group, chat_id, message_id, callback_query_id):
    """معالجة إكمال الإعدادات في المجموعة"""
    try:
        # التحقق من أن المجموعة نشطة
        if not group.is_active:
            answer_callback_query(callback_query_id, "⚠️ المجموعة غير نشطة", True)
            return False
        
        # تحديث رسالة الإعدادات
        from study_bot.group_menus import GROUP_SETTINGS_MENU
        
        settings_message = f"""⚙️ <b>إعدادات المجموعة</b>

<b>اسم المجموعة:</b> {group.title}
<b>الرسائل التحفيزية:</b> {'✅ مفعلة' if group.motivation_enabled else '❌ معطلة'}
<b>نوع الجدول:</b> {get_schedule_type_text(group.schedule_type)}

اختر الإعداد الذي تريد تغييره:
"""
        
        # تعديل الرسالة
        edit_group_message(chat_id, message_id, settings_message, GROUP_SETTINGS_MENU)
        
        # الرد على الاستعلام
        answer_callback_query(callback_query_id, "✅ تم فتح إعدادات المجموعة")
        
        return True
    except Exception as e:
        logger.error(f"خطأ في معالجة إكمال الإعدادات في المجموعة: {e}")
        logger.error(traceback.format_exc())
        answer_callback_query(callback_query_id, "❌ حدث خطأ أثناء معالجة الإعدادات", True)
        return False


def handle_group_setup_private(group, chat_id, user_id, message_id, callback_query_id):
    """معالجة إكمال الإعدادات في الخاص"""
    try:
        # التحقق من أن المجموعة نشطة
        if not group.is_active:
            answer_callback_query(callback_query_id, "⚠️ المجموعة غير نشطة", True)
            return False
        
        # التحقق من أن المستخدم هو مشرف المجموعة
        if user_id != group.admin_id:
            answer_callback_query(callback_query_id, "⚠️ يجب أن تكون مشرف المجموعة", True)
            return False
        
        # إرسال رابط فتح الإعدادات في الخاص
        from study_bot.group_menus import OPEN_PRIVATE_SETUP_MENU
        
        private_setup_message = f"""⚙️ <b>إعدادات المجموعة</b>

يمكنك إدارة إعدادات المجموعة "{group.title}" من خلال المحادثة الخاصة مع البوت.

اضغط على الزر أدناه لفتح البوت والإعدادات في الخاص:
"""
        
        # تعديل الرسالة
        edit_group_message(chat_id, message_id, private_setup_message, OPEN_PRIVATE_SETUP_MENU)
        
        # الرد على الاستعلام
        answer_callback_query(callback_query_id, "✅ تم إرسال رابط الإعدادات في الخاص")
        
        return True
    except Exception as e:
        logger.error(f"خطأ في معالجة إكمال الإعدادات في الخاص: {e}")
        logger.error(traceback.format_exc())
        answer_callback_query(callback_query_id, "❌ حدث خطأ أثناء معالجة الإعدادات", True)
        return False


def handle_group_toggle_motivation(group, chat_id, message_id, callback_query_id):
    """تفعيل/إيقاف الرسائل التحفيزية"""
    try:
        # التحقق من أن المجموعة نشطة
        if not group.is_active:
            answer_callback_query(callback_query_id, "⚠️ المجموعة غير نشطة", True)
            return False
        
        # تبديل حالة الرسائل التحفيزية
        group.motivation_enabled = not group.motivation_enabled
        db.session.commit()
        
        # تحديث رسالة الإعدادات
        from study_bot.group_menus import GROUP_SETTINGS_MENU
        
        settings_message = f"""⚙️ <b>إعدادات المجموعة</b>

<b>اسم المجموعة:</b> {group.title}
<b>الرسائل التحفيزية:</b> {'✅ مفعلة' if group.motivation_enabled else '❌ معطلة'}
<b>نوع الجدول:</b> {get_schedule_type_text(group.schedule_type)}

اختر الإعداد الذي تريد تغييره:
"""
        
        # تعديل الرسالة
        edit_group_message(chat_id, message_id, settings_message, GROUP_SETTINGS_MENU)
        
        # الرد على الاستعلام
        status = "تفعيل" if group.motivation_enabled else "إيقاف"
        answer_callback_query(callback_query_id, f"✅ تم {status} الرسائل التحفيزية")
        
        return True
    except Exception as e:
        logger.error(f"خطأ في تفعيل/إيقاف الرسائل التحفيزية: {e}")
        logger.error(traceback.format_exc())
        answer_callback_query(callback_query_id, "❌ حدث خطأ أثناء تغيير الإعدادات", True)
        return False


def handle_group_send_motivation(group, chat_id, callback_query_id):
    """إرسال رسالة تحفيزية فورية للمجموعة"""
    try:
        # التحقق من أن المجموعة نشطة
        if not group.is_active:
            answer_callback_query(callback_query_id, "⚠️ المجموعة غير نشطة", True)
            return False
        
        # إرسال رسالة تحفيزية
        from study_bot.group_tasks import send_motivation_to_group
        result = send_motivation_to_group(group.id)
        
        if result:
            # الرد على الاستعلام
            answer_callback_query(callback_query_id, "✅ تم إرسال رسالة تحفيزية")
            return True
        else:
            answer_callback_query(callback_query_id, "❌ فشل إرسال الرسالة التحفيزية", True)
            return False
    except Exception as e:
        logger.error(f"خطأ في إرسال رسالة تحفيزية فورية: {e}")
        logger.error(traceback.format_exc())
        answer_callback_query(callback_query_id, "❌ حدث خطأ أثناء إرسال الرسالة", True)
        return False


def handle_group_schedule_settings(group, chat_id, message_id, callback_query_id):
    """عرض إعدادات الجدول"""
    try:
        # التحقق من أن المجموعة نشطة
        if not group.is_active:
            answer_callback_query(callback_query_id, "⚠️ المجموعة غير نشطة", True)
            return False
        
        # إعداد رسالة إعدادات الجدول
        from study_bot.group_menus import GROUP_SCHEDULE_MENU
        
        schedule_message = f"""📅 <b>إعدادات الجدول</b>

<b>نوع الجدول الحالي:</b> {get_schedule_type_text(group.schedule_type)}

اختر نوع الجدول الذي تريد تفعيله:
"""
        
        # تعديل الرسالة
        edit_group_message(chat_id, message_id, schedule_message, GROUP_SCHEDULE_MENU)
        
        # الرد على الاستعلام
        answer_callback_query(callback_query_id, "✅ تم فتح إعدادات الجدول")
        
        return True
    except Exception as e:
        logger.error(f"خطأ في عرض إعدادات الجدول: {e}")
        logger.error(traceback.format_exc())
        answer_callback_query(callback_query_id, "❌ حدث خطأ أثناء فتح إعدادات الجدول", True)
        return False


def handle_group_schedule_morning(group, chat_id, message_id, callback_query_id):
    """عرض تفاصيل الجدول الصباحي"""
    try:
        # التحقق من أن المجموعة نشطة
        if not group.is_active:
            answer_callback_query(callback_query_id, "⚠️ المجموعة غير نشطة", True)
            return False
        
        # إعداد رسالة تفاصيل الجدول الصباحي
        from study_bot.group_menus import GROUP_CONFIRM_MORNING_MENU
        
        morning_message = f"""🌞 <b>الجدول الصباحي</b>

الجدول الصباحي يساعد على الالتزام بالمذاكرة طوال اليوم من الصباح الباكر حتى المساء.

<b>مميزات الجدول الصباحي:</b>
• تنظيم كامل اليوم الدراسي
• توزيع فترات المذاكرة والراحة
• تذكير بأوقات الصلاة
• مراقبة التقدم وتسجيل النقاط

<b>أوقات المهام الرئيسية:</b>
• 4:25 ص - صلاة الفجر
• 8:30 ص - بدء المذاكرة
• 12:51 م - صلاة الظهر
• 4:28 م - صلاة العصر
• 9:30 م - تقييم اليوم

هل تريد تفعيل الجدول الصباحي؟
"""
        
        # تعديل الرسالة
        edit_group_message(chat_id, message_id, morning_message, GROUP_CONFIRM_MORNING_MENU)
        
        # الرد على الاستعلام
        answer_callback_query(callback_query_id, "✅ تم عرض تفاصيل الجدول الصباحي")
        
        return True
    except Exception as e:
        logger.error(f"خطأ في عرض تفاصيل الجدول الصباحي: {e}")
        logger.error(traceback.format_exc())
        answer_callback_query(callback_query_id, "❌ حدث خطأ أثناء عرض التفاصيل", True)
        return False


def handle_group_schedule_evening(group, chat_id, message_id, callback_query_id):
    """عرض تفاصيل الجدول المسائي"""
    try:
        # التحقق من أن المجموعة نشطة
        if not group.is_active:
            answer_callback_query(callback_query_id, "⚠️ المجموعة غير نشطة", True)
            return False
        
        # إعداد رسالة تفاصيل الجدول المسائي
        from study_bot.group_menus import GROUP_CONFIRM_EVENING_MENU
        
        evening_message = f"""🌙 <b>الجدول المسائي</b>

الجدول المسائي مخصص للدراسة في الفترة المسائية، مناسب لمن لديهم التزامات صباحية أو يفضلون المذاكرة مساءً.

<b>مميزات الجدول المسائي:</b>
• تنظيم فترة المساء للدراسة
• التركيز على المراجعة وحل الواجبات
• تذكير بأوقات الصلاة المسائية
• تحفيز على النوم المبكر

<b>أوقات المهام الرئيسية:</b>
• 3:00 م - بدء المعسكر المسائي
• 3:30 م - المراجعة
• 7:40 م - صلاة المغرب
• 9:00 م - صلاة العشاء
• 10:30 م - تقييم اليوم
• 11:00 م - النوم المبكر

هل تريد تفعيل الجدول المسائي؟
"""
        
        # تعديل الرسالة
        edit_group_message(chat_id, message_id, evening_message, GROUP_CONFIRM_EVENING_MENU)
        
        # الرد على الاستعلام
        answer_callback_query(callback_query_id, "✅ تم عرض تفاصيل الجدول المسائي")
        
        return True
    except Exception as e:
        logger.error(f"خطأ في عرض تفاصيل الجدول المسائي: {e}")
        logger.error(traceback.format_exc())
        answer_callback_query(callback_query_id, "❌ حدث خطأ أثناء عرض التفاصيل", True)
        return False


def handle_group_confirm_morning(group, chat_id, message_id, callback_query_id):
    """تأكيد تفعيل الجدول الصباحي"""
    try:
        # التحقق من أن المجموعة نشطة
        if not group.is_active:
            answer_callback_query(callback_query_id, "⚠️ المجموعة غير نشطة", True)
            return False
        
        # تحديث نوع الجدول للمجموعة
        group.schedule_type = 'morning'
        db.session.commit()
        
        # إرسال رسالة تأكيد
        confirmation_message = f"""✅ <b>تم تفعيل الجدول الصباحي</b>

تم تفعيل الجدول الصباحي بنجاح في مجموعة "{group.title}".

• سيتم إرسال رسالة الجدول الصباحي في تمام الساعة 3:00 صباحاً يومياً.
• سيتلقى المشاركون رسائل تذكير بالمهام خلال اليوم.
• يمكن للمشاركين كسب النقاط عند إكمال المهام.

للانضمام للجدول الصباحي، يجب الرد على رسالة الجدول عند إرسالها.
"""
        
        # تعديل الرسالة
        edit_group_message(chat_id, message_id, confirmation_message)
        
        # الرد على الاستعلام
        answer_callback_query(callback_query_id, "✅ تم تفعيل الجدول الصباحي بنجاح")
        
        # إرسال رسالة الجدول الصباحي الآن
        from study_bot.group_tasks import send_group_morning_message
        result = send_group_morning_message(chat_id)
        
        return True
    except Exception as e:
        logger.error(f"خطأ في تأكيد تفعيل الجدول الصباحي: {e}")
        logger.error(traceback.format_exc())
        answer_callback_query(callback_query_id, "❌ حدث خطأ أثناء تفعيل الجدول", True)
        return False


def handle_group_confirm_evening(group, chat_id, message_id, callback_query_id):
    """تأكيد تفعيل الجدول المسائي"""
    try:
        # التحقق من أن المجموعة نشطة
        if not group.is_active:
            answer_callback_query(callback_query_id, "⚠️ المجموعة غير نشطة", True)
            return False
        
        # تحديث نوع الجدول للمجموعة
        group.schedule_type = 'evening'
        db.session.commit()
        
        # إرسال رسالة تأكيد
        confirmation_message = f"""✅ <b>تم تفعيل الجدول المسائي</b>

تم تفعيل الجدول المسائي بنجاح في مجموعة "{group.title}".

• سيتم إرسال رسالة الجدول المسائي في تمام الساعة 3:00 مساءً يومياً.
• سيتلقى المشاركون رسائل تذكير بالمهام خلال المساء.
• يمكن للمشاركين كسب النقاط عند إكمال المهام.

للانضمام للجدول المسائي، يجب الرد على رسالة الجدول عند إرسالها.
"""
        
        # تعديل الرسالة
        edit_group_message(chat_id, message_id, confirmation_message)
        
        # الرد على الاستعلام
        answer_callback_query(callback_query_id, "✅ تم تفعيل الجدول المسائي بنجاح")
        
        # إرسال رسالة الجدول المسائي الآن
        from study_bot.group_tasks import send_group_evening_message
        result = send_group_evening_message(chat_id)
        
        return True
    except Exception as e:
        logger.error(f"خطأ في تأكيد تفعيل الجدول المسائي: {e}")
        logger.error(traceback.format_exc())
        answer_callback_query(callback_query_id, "❌ حدث خطأ أثناء تفعيل الجدول", True)
        return False


def handle_join_morning_schedule(group, user_id, chat_id, callback_query_id):
    """معالجة انضمام المستخدم للجدول الصباحي"""
    try:
        # التحقق من أن المجموعة نشطة
        if not group.is_active:
            answer_callback_query(callback_query_id, "⚠️ المجموعة غير نشطة", True)
            return False
        
        # التحقق من نوع الجدول
        if group.schedule_type != 'morning':
            answer_callback_query(callback_query_id, "⚠️ الجدول الصباحي غير مفعل في هذه المجموعة", True)
            return False
        
        # الحصول على أو إنشاء المستخدم
        from study_bot.models import User, GroupParticipant
        
        user = User.query.filter_by(telegram_id=user_id).first()
        if not user:
            # إنشاء مستخدم جديد
            user = User(
                telegram_id=user_id,
                is_active=True,
                preferred_schedule='morning'
            )
            db.session.add(user)
            db.session.commit()
        
        # التحقق من مشاركة المستخدم في المجموعة
        participant = GroupParticipant.query.filter_by(
            group_id=group.id,
            user_id=user.id
        ).first()
        
        if not participant:
            # إنشاء مشارك جديد
            participant = GroupParticipant(
                group_id=group.id,
                user_id=user.id,
                join_date=datetime.utcnow(),
                is_active=True
            )
            db.session.add(participant)
            db.session.commit()
        elif not participant.is_active:
            # إعادة تنشيط المشارك
            participant.is_active = True
            db.session.commit()
        
        # منح نقاط الانضمام
        from study_bot.config import MORNING_POINTS
        join_points = MORNING_POINTS.get('join', 5)
        
        # تحديث نقاط المستخدم والمشارك
        user.morning_points += join_points
        user.total_points += join_points
        participant.morning_points += join_points
        participant.total_points += join_points
        db.session.commit()
        
        # الرد على الاستعلام
        answer_callback_query(callback_query_id, f"✅ تم انضمامك للجدول الصباحي! +{join_points} نقطة", True)
        
        return True
    except Exception as e:
        logger.error(f"خطأ في معالجة انضمام المستخدم للجدول الصباحي: {e}")
        logger.error(traceback.format_exc())
        answer_callback_query(callback_query_id, "❌ حدث خطأ أثناء الانضمام", True)
        return False


def handle_join_evening_schedule(group, user_id, chat_id, callback_query_id):
    """معالجة انضمام المستخدم للجدول المسائي"""
    try:
        # التحقق من أن المجموعة نشطة
        if not group.is_active:
            answer_callback_query(callback_query_id, "⚠️ المجموعة غير نشطة", True)
            return False
        
        # التحقق من نوع الجدول
        if group.schedule_type != 'evening':
            answer_callback_query(callback_query_id, "⚠️ الجدول المسائي غير مفعل في هذه المجموعة", True)
            return False
        
        # الحصول على أو إنشاء المستخدم
        from study_bot.models import User, GroupParticipant
        
        user = User.query.filter_by(telegram_id=user_id).first()
        if not user:
            # إنشاء مستخدم جديد
            user = User(
                telegram_id=user_id,
                is_active=True,
                preferred_schedule='evening'
            )
            db.session.add(user)
            db.session.commit()
        
        # التحقق من مشاركة المستخدم في المجموعة
        participant = GroupParticipant.query.filter_by(
            group_id=group.id,
            user_id=user.id
        ).first()
        
        if not participant:
            # إنشاء مشارك جديد
            participant = GroupParticipant(
                group_id=group.id,
                user_id=user.id,
                join_date=datetime.utcnow(),
                is_active=True
            )
            db.session.add(participant)
            db.session.commit()
        elif not participant.is_active:
            # إعادة تنشيط المشارك
            participant.is_active = True
            db.session.commit()
        
        # منح نقاط الانضمام
        from study_bot.config import EVENING_POINTS
        join_points = EVENING_POINTS.get('join', 5)
        
        # تحديث نقاط المستخدم والمشارك
        user.evening_points += join_points
        user.total_points += join_points
        participant.evening_points += join_points
        participant.total_points += join_points
        db.session.commit()
        
        # الرد على الاستعلام
        answer_callback_query(callback_query_id, f"✅ تم انضمامك للجدول المسائي! +{join_points} نقطة", True)
        
        return True
    except Exception as e:
        logger.error(f"خطأ في معالجة انضمام المستخدم للجدول المسائي: {e}")
        logger.error(traceback.format_exc())
        answer_callback_query(callback_query_id, "❌ حدث خطأ أثناء الانضمام", True)
        return False


def handle_group_schedule_custom(group, chat_id, message_id, callback_query_id):
    """عرض تفاصيل إنشاء الجدول المخصص"""
    try:
        # التحقق من أن المجموعة نشطة
        if not group.is_active:
            answer_callback_query(callback_query_id, "⚠️ المجموعة غير نشطة", True)
            return False
        
        # إعداد رسالة تفاصيل الجدول المخصص
        from study_bot.group_menus import GROUP_CONFIRM_CUSTOM_MENU
        
        custom_message = f"""✏️ <b>المعسكر المخصص</b>

المعسكر المخصص يتيح لك إنشاء معسكرات دراسية بجداول وأوقات مخصصة حسب احتياجات المجموعة.

<b>مميزات المعسكر المخصص:</b>
• تحديد مواعيد المهام بشكل مخصص
• إنشاء معسكرات لمدة محددة
• إضافة مهام دراسية متنوعة
• متابعة أداء المشاركين بدقة

<b>كيفية إنشاء معسكر مخصص:</b>
1. اختر "تأكيد تفعيل المعسكر المخصص" أدناه
2. استخدم الأمر /createcamp لإنشاء معسكر جديد
3. استخدم الأمر /addtask لإضافة مهام للمعسكر

مثال:
/createcamp معسكر الرياضيات | مراجعة مادة الرياضيات للاختبار النهائي | 2025-05-10 08:00 | 2025-05-20 22:00

هل تريد تفعيل نظام المعسكرات المخصصة؟
"""
        
        # تعديل الرسالة
        edit_group_message(chat_id, message_id, custom_message, GROUP_CONFIRM_CUSTOM_MENU)
        
        # الرد على الاستعلام
        answer_callback_query(callback_query_id, "✅ تم عرض تفاصيل المعسكر المخصص")
        
        return True
    except Exception as e:
        logger.error(f"خطأ في عرض تفاصيل المعسكر المخصص: {e}")
        logger.error(traceback.format_exc())
        answer_callback_query(callback_query_id, "❌ حدث خطأ أثناء عرض التفاصيل", True)
        return False


def handle_group_confirm_custom(group, chat_id, message_id, callback_query_id):
    """تأكيد تفعيل الجدول المخصص"""
    try:
        # التحقق من أن المجموعة نشطة
        if not group.is_active:
            answer_callback_query(callback_query_id, "⚠️ المجموعة غير نشطة", True)
            return False
        
        # تحديث نوع الجدول للمجموعة
        group.schedule_type = 'custom'
        db.session.commit()
        
        # إرسال رسالة تأكيد
        confirmation_message = f"""✅ <b>تم تفعيل نظام المعسكرات المخصصة</b>

تم تفعيل نظام المعسكرات المخصصة بنجاح في مجموعة "{group.title}".

<b>الأوامر المتاحة:</b>
• /createcamp - إنشاء معسكر جديد
• /addtask - إضافة مهمة لمعسكر
• /campreport - طلب تقرير عن معسكر

<b>مثال لإنشاء معسكر:</b>
/createcamp معسكر الرياضيات | مراجعة مادة الرياضيات للاختبار النهائي | 2025-05-10 08:00 | 2025-05-20 22:00

<b>مثال لإضافة مهمة:</b>
/addtask 1 | مذاكرة الفصل الأول | مراجعة الفصل الأول من كتاب الرياضيات | 2025-05-10 16:30 | 5 | 30

<b>مثال لطلب تقرير:</b>
/campreport 1
"""
        
        # تعديل الرسالة
        edit_group_message(chat_id, message_id, confirmation_message)
        
        # الرد على الاستعلام
        answer_callback_query(callback_query_id, "✅ تم تفعيل نظام المعسكرات المخصصة بنجاح")
        
        return True
    except Exception as e:
        logger.error(f"خطأ في تأكيد تفعيل المعسكر المخصص: {e}")
        logger.error(traceback.format_exc())
        answer_callback_query(callback_query_id, "❌ حدث خطأ أثناء تفعيل المعسكر", True)
        return False


def handle_join_custom_schedule(group, user_id, chat_id, callback_query_id):
    """معالجة انضمام المستخدم للجدول المخصص"""
    try:
        # التحقق من أن المجموعة نشطة
        if not group.is_active:
            answer_callback_query(callback_query_id, "⚠️ المجموعة غير نشطة", True)
            return False
        
        # التحقق من نوع الجدول
        if group.schedule_type != 'custom':
            answer_callback_query(callback_query_id, "⚠️ المعسكر المخصص غير مفعل في هذه المجموعة", True)
            return False
        
        # الحصول على أو إنشاء المستخدم
        from study_bot.models import User, GroupParticipant
        
        user = User.query.filter_by(telegram_id=user_id).first()
        if not user:
            # إنشاء مستخدم جديد
            user = User(
                telegram_id=user_id,
                is_active=True,
                preferred_schedule='custom'
            )
            db.session.add(user)
            db.session.commit()
        
        # التحقق من مشاركة المستخدم في المجموعة
        participant = GroupParticipant.query.filter_by(
            group_id=group.id,
            user_id=user.id
        ).first()
        
        if not participant:
            # إنشاء مشارك جديد
            participant = GroupParticipant(
                group_id=group.id,
                user_id=user.id,
                join_date=datetime.utcnow(),
                is_active=True
            )
            db.session.add(participant)
            db.session.commit()
        elif not participant.is_active:
            # إعادة تنشيط المشارك
            participant.is_active = True
            db.session.commit()
        
        # منح نقاط الانضمام
        from study_bot.config import POINTS_CONFIG
        join_points = POINTS_CONFIG.get('join', 5)
        
        # تحديث نقاط المستخدم والمشارك
        user.total_points += join_points
        participant.custom_points += join_points
        participant.total_points += join_points
        db.session.commit()
        
        # الرد على الاستعلام
        answer_callback_query(callback_query_id, f"✅ تم انضمامك للمعسكر المخصص! +{join_points} نقطة", True)
        
        return True
    except Exception as e:
        logger.error(f"خطأ في معالجة انضمام المستخدم للمعسكر المخصص: {e}")
        logger.error(traceback.format_exc())
        answer_callback_query(callback_query_id, "❌ حدث خطأ أثناء الانضمام", True)
        return False


def handle_group_schedule_reset(group, chat_id, message_id, callback_query_id):
    """إعادة تهيئة الجدول"""
    try:
        # التحقق من أن المجموعة نشطة
        if not group.is_active:
            answer_callback_query(callback_query_id, "⚠️ المجموعة غير نشطة", True)
            return False
        
        # تحديث نوع الجدول للمجموعة
        previous_schedule = group.schedule_type
        group.schedule_type = 'none'
        db.session.commit()
        
        # إرسال رسالة تأكيد
        reset_message = f"""✅ <b>تم إعادة تهيئة الجدول</b>

تم إيقاف الجدول بنجاح في مجموعة "{group.title}".

<b>الجدول السابق:</b> {get_schedule_type_text(previous_schedule)}
<b>الجدول الحالي:</b> غير محدد

يمكنك تفعيل جدول جديد من إعدادات الجدول.
"""
        
        # تعديل الرسالة
        edit_group_message(chat_id, message_id, reset_message)
        
        # الرد على الاستعلام
        answer_callback_query(callback_query_id, "✅ تم إعادة تهيئة الجدول بنجاح")
        
        return True
    except Exception as e:
        logger.error(f"خطأ في إعادة تهيئة الجدول: {e}")
        logger.error(traceback.format_exc())
        answer_callback_query(callback_query_id, "❌ حدث خطأ أثناء إعادة التهيئة", True)
        return False


def handle_back_to_group_settings(group, chat_id, message_id, callback_query_id):
    """العودة إلى إعدادات المجموعة"""
    try:
        # التحقق من أن المجموعة نشطة
        if not group.is_active:
            answer_callback_query(callback_query_id, "⚠️ المجموعة غير نشطة", True)
            return False
        
        # تحديث رسالة الإعدادات
        from study_bot.group_menus import GROUP_SETTINGS_MENU
        
        settings_message = f"""⚙️ <b>إعدادات المجموعة</b>

<b>اسم المجموعة:</b> {group.title}
<b>الرسائل التحفيزية:</b> {'✅ مفعلة' if group.motivation_enabled else '❌ معطلة'}
<b>نوع الجدول:</b> {get_schedule_type_text(group.schedule_type)}

اختر الإعداد الذي تريد تغييره:
"""
        
        # تعديل الرسالة
        edit_group_message(chat_id, message_id, settings_message, GROUP_SETTINGS_MENU)
        
        # الرد على الاستعلام
        answer_callback_query(callback_query_id, "✅ تم العودة إلى إعدادات المجموعة")
        
        return True
    except Exception as e:
        logger.error(f"خطأ في العودة إلى إعدادات المجموعة: {e}")
        logger.error(traceback.format_exc())
        answer_callback_query(callback_query_id, "❌ حدث خطأ أثناء العودة للإعدادات", True)
        return False


def get_schedule_type_text(schedule_type):
    """الحصول على نص نوع الجدول بالعربية"""
    if schedule_type == 'morning':
        return "🌞 الجدول الصباحي"
    elif schedule_type == 'evening':
        return "🌙 الجدول المسائي"
    elif schedule_type == 'custom':
        return "✏️ المعسكر المخصص"
    else:
        return "❌ غير محدد"