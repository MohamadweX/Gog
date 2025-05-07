#!/usr/bin/env python3
"""
إدارة المعسكرات من المحادثات الخاصة
يحتوي على وظائف للتعامل مع إعدادات المعسكرات من المحادثة الخاصة بمشرف المجموعة
"""

import json
import random
from datetime import datetime, timedelta

from study_bot.config import TELEGRAM_API_URL, logger
from study_bot.models import User, Group, GroupParticipant, db
from study_bot.camps_models import CustomCamp, CampTask, CampParticipant
from study_bot.bot import send_message
from study_bot.group_handlers import send_group_message, answer_callback_query

# ملف تخزين حالة الإعدادات المؤقتة
private_setup_states = {}

# مخزن مؤقت لبيانات إنشاء المعسكر
camp_creation_data = {}

# إدارة المجموعات من الخاص
def handle_private_group_setup(user_id, chat_id):
    """
    معالجة إعدادات المجموعة في الخاص
    تتيح للمشرف إدارة معسكرات مجموعته من محادثته الخاصة مع البوت
    """
    # التحقق من المجموعات التي يشرف عليها المستخدم
    admin_groups = Group.query.filter_by(admin_id=user_id, is_active=True).all()
    
    if not admin_groups:
        send_message(chat_id, "❗ أنت لست مشرفًا على أي مجموعة حاليًا. الرجاء إضافة البوت إلى مجموعة وتفعيله لتصبح مشرفًا.")
        return False
    
    # عرض قائمة بالمجموعات التي يشرف عليها المستخدم
    keyboard = []
    for group in admin_groups:
        keyboard.append([{
            'text': f"{group.title} (المعرف: {group.telegram_id})",
            'callback_data': f"group_setup_{group.telegram_id}"
        }])
    
    # إضافة زر العودة
    keyboard.append([{'text': '📥 العودة للقائمة الرئيسية', 'callback_data': 'back_to_main'}])
    
    # إرسال رسالة الإعدادات
    message = f"""👥 <b>إدارة مجموعاتك</b>
    
لديك {len(admin_groups)} مجموعة/مجموعات مفعّلة كمشرف.
اختر مجموعة لإدارتها:
"""
    
    markup = {
        'inline_keyboard': keyboard
    }
    
    send_message(chat_id, message, markup)
    return True

def handle_admin_groups(user_id, chat_id, message_id=None):
    """إدارة المجموعات كمشرف"""
    # التحقق من المجموعات التي يشرف عليها المستخدم
    admin_groups = Group.query.filter_by(admin_id=user_id, is_active=True).all()
    
    if not admin_groups:
        send_message(chat_id, "❗ أنت لست مشرفًا على أي مجموعة حاليًا. الرجاء إضافة البوت إلى مجموعة وتفعيله لتصبح مشرفًا.")
        return False
    
    # عرض قائمة بالمجموعات التي يشرف عليها المستخدم
    keyboard = []
    for group in admin_groups:
        keyboard.append([{
            'text': f"{group.title} (المعرف: {group.telegram_id})",
            'callback_data': f"group_setup_{group.telegram_id}"
        }])
    
    # إضافة زر العودة
    keyboard.append([{'text': '📥 العودة للقائمة الرئيسية', 'callback_data': 'back_to_main'}])
    
    # إرسال رسالة الإعدادات
    message = f"""👥 <b>إدارة مجموعاتك</b>
    
لديك {len(admin_groups)} مجموعة/مجموعات مفعّلة كمشرف.
اختر مجموعة لإدارتها:
"""
    
    markup = {
        'inline_keyboard': keyboard
    }
    
    send_message(chat_id, message, markup)
    return True

def handle_private_camp_callbacks(callback_data, user_id, chat_id, callback_query_id):
    """معالجة الاستجابات للأزرار المتعلقة بالمعسكرات في المحادثة الخاصة"""
    try:
        # معالجة زر العودة للقائمة الرئيسية
        if callback_data == 'back_to_main':
            from study_bot.bot import show_main_menu
            show_main_menu(chat_id)
            return True
            
        # معالجة زر إنشاء معسكر جديد
        elif callback_data == 'create_new_camp':
            from study_bot.admin_commands import handle_newcamp_command
            handle_newcamp_command({'chat_id': chat_id, 'user_id': user_id})
            return True
            
        # معالجة زر تخصيص معسكر
        elif callback_data == 'customize_camp':
            from study_bot.admin_commands import handle_customcamp_command
            handle_customcamp_command({'chat_id': chat_id, 'user_id': user_id})
            return True
        
        # معالجة زر إنشاء معسكر لمجموعة محددة
        elif callback_data.startswith('new_camp_for_group:') or callback_data.startswith('create_camp_setup:'):
            try:
                group_id = None
                if callback_data.startswith('new_camp_for_group:'):
                    group_id = int(callback_data.split(':')[1])
                else:  # create_camp_setup
                    group_id = int(callback_data.split(':')[1])
                    
                answer_callback_query(callback_query_id, "جاري إعداد المعسكر الجديد...")
                return handle_create_camp_step1(user_id, chat_id, group_id)
            except Exception as e:
                logger.error(f"خطأ في معالجة زر إنشاء معسكر لمجموعة: {e}")
                answer_callback_query(callback_query_id, "حدث خطأ أثناء إعداد المعسكر", show_alert=True)
                return False
            
        # معالجة ردود أزرار إدارة المجموعات
        elif callback_data.startswith('group_setup_'):
            group_telegram_id = int(callback_data.split('_')[2])
            # هنا يمكن إضافة المزيد من المنطق لإدارة المجموعة المحددة
            # مثل عرض إعدادات المجموعة أو المعسكرات فيها
            return handle_group_settings(user_id, chat_id, group_telegram_id)
            
        # معالجة ردود أزرار إدارة المعسكرات
        # معالجة زر عرض معسكرات المجموعة
        elif callback_data.startswith('group_camps:'):
            # عرض معسكرات مجموعة محددة
            try:
                group_id = int(callback_data.split(':')[1])
                answer_callback_query(callback_query_id, "جاري عرض معسكرات المجموعة...")
                return handle_group_camps(user_id, chat_id, group_id)
            except Exception as e:
                logger.error(f"خطأ في عرض معسكرات المجموعة: {e}")
                answer_callback_query(callback_query_id, "حدث خطأ أثناء عرض المعسكرات", show_alert=True)
                return False
        
        # معالجة زر عرض تفاصيل معسكر
        elif callback_data.startswith('camp_details_') or callback_data.startswith('manage_camp:'):
            # التعامل مع كلا النمطين المحتملين للزر
            try:
                camp_id = None
                if callback_data.startswith('camp_details_'):
                    camp_id = int(callback_data.split('_')[2])
                else:
                    camp_id = int(callback_data.split(':')[1])
                return handle_camp_details(user_id, chat_id, camp_id)
            except Exception as e:
                logger.error(f"خطأ في عرض تفاصيل المعسكر: {e}")
                answer_callback_query(callback_query_id, "حدث خطأ أثناء عرض تفاصيل المعسكر", show_alert=True)
                return False
        
        # أزرار الانتقال بين القوائم
        elif callback_data == 'admin_camps':
            # العودة إلى قائمة المعسكرات
            answer_callback_query(callback_query_id, "جاري عرض قائمة المعسكرات...")
            return handle_admin_camps(user_id, chat_id)
            
        elif callback_data == 'admin_groups':
            # العودة إلى قائمة المجموعات
            answer_callback_query(callback_query_id, "جاري عرض قائمة المجموعات...")
            return handle_admin_groups(user_id, chat_id)
            
        # معالجة إجراءات إنشاء المعسكر
        elif callback_data == 'camp_create_confirm':
            # تأكيد إنشاء المعسكر
            return handle_create_camp_confirm(user_id, chat_id, callback_query_id)
            
        elif callback_data == 'camp_create_cancel':
            # إلغاء إنشاء المعسكر
            if user_id in camp_creation_data:
                del camp_creation_data[user_id]
            if user_id in private_setup_states:
                del private_setup_states[user_id]
                
            answer_callback_query(callback_query_id, "تم إلغاء إنشاء المعسكر")
            
            # الرجوع إلى قائمة المعسكرات
            from study_bot.admin_commands import handle_camps_command
            handle_camps_command({'chat_id': chat_id, 'user_id': user_id})
            return True
            
        else:
            # إذا لم يتم التعامل مع رد الزر، إرجاع False
            return False
    except Exception as e:
        logger.error(f"خطأ في معالجة رد زر المعسكر الخاص: {e}")
        answer_callback_query(callback_query_id, "❌ حدث خطأ أثناء معالجة طلبك")
        return False


def handle_create_camp_step1(user_id, chat_id, group_id):
    """الخطوة الأولى في إنشاء معسكر جديد: إدخال اسم المعسكر"""
    try:
        # التحقق من أن المجموعة موجودة
        group = Group.query.get(group_id)
        if not group or not group.is_active:
            send_message(chat_id, "❗ لم يتم العثور على المجموعة المطلوبة أو أنها غير نشطة.")
            return False
        
        # التحقق من أن المستخدم هو مشرف المجموعة
        if group.admin_id != user_id:
            send_message(chat_id, "❗ أنت لست مشرفًا على هذه المجموعة.")
            return False
        
        # حفظ معلومات المجموعة في المخزن المؤقت
        if user_id not in camp_creation_data:
            camp_creation_data[user_id] = {}
        
        camp_creation_data[user_id]['group_id'] = group_id
        camp_creation_data[user_id]['step'] = 1  # خطوة إدخال الاسم
        
        # إرسال رسالة لإدخال اسم المعسكر
        message = f"""🏝️ <b>إنشاء معسكر جديد</b> - الخطوة 1/5

<b>المجموعة:</b> {group.title}

الرجاء إرسال اسم المعسكر الدراسي الجديد.
(مثل: معسكر التفوق الدراسي الأول)

يمكنك إلغاء العملية بأي وقت بالضغط على زر الإلغاء أدناه.
"""
        
        # إنشاء زر الإلغاء
        keyboard = [
            [{'text': '❌ إلغاء إنشاء المعسكر', 'callback_data': 'camp_create_cancel'}]
        ]
        
        markup = {'inline_keyboard': keyboard}
        send_message(chat_id, message, markup)
        
        # تعيين حالة المستخدم لاستقبال اسم المعسكر
        private_setup_states[user_id] = 'waiting_camp_name'
        
        return True
    except Exception as e:
        logger.error(f"خطأ في إنشاء معسكر - الخطوة 1: {e}")
        send_message(chat_id, "❗ حدث خطأ أثناء إعداد معسكر جديد. يرجى المحاولة مرة أخرى.")
        return False


def handle_create_camp_confirm(user_id, chat_id, callback_query_id):
    """تأكيد إنشاء المعسكر وحفظه في قاعدة البيانات"""
    try:
        # التحقق من وجود البيانات
        if user_id not in camp_creation_data:
            answer_callback_query(callback_query_id, "❗ لم يتم العثور على بيانات المعسكر. يرجى البدء من جديد.")
            return False
        
        # استخراج بيانات المعسكر
        camp_data = camp_creation_data[user_id]
        
        # التحقق من اكتمال البيانات
        required_fields = ['group_id', 'name', 'description', 'start_date', 'end_date']
        if not all(field in camp_data for field in required_fields):
            answer_callback_query(callback_query_id, "❗ بيانات المعسكر غير مكتملة. يرجى إدخال جميع البيانات المطلوبة.")
            return False
        
        # إنشاء معسكر جديد
        try:
            # استخدام وحدة إنشاء المعسكرات
            from study_bot.custom_camps import create_custom_camp
            
            new_camp = create_custom_camp(
                group_id=camp_data['group_id'],
                admin_id=user_id,
                camp_name=camp_data['name'],
                description=camp_data['description'],
                start_date=camp_data['start_date'],
                end_date=camp_data['end_date'],
                max_participants=camp_data.get('max_participants', 0)
            )
            
            # إذا تم إنشاء المعسكر بنجاح
            if new_camp:
                answer_callback_query(callback_query_id, "✅ تم إنشاء المعسكر بنجاح!")
                
                # إرسال رسالة تأكيد
                group = Group.query.get(camp_data['group_id'])
                success_message = f"""🏝️ <b>تم إنشاء المعسكر بنجاح!</b>
                
<b>اسم المعسكر:</b> {camp_data['name']}
<b>المجموعة:</b> {group.title}
<b>تاريخ البداية:</b> {camp_data['start_date'].strftime('%Y-%m-%d')}
<b>تاريخ النهاية:</b> {camp_data['end_date'].strftime('%Y-%m-%d')}

يمكنك الآن إضافة مهام للمعسكر.
"""
                
                # أزرار الإجراءات التالية
                keyboard = [
                    [{'text': '➕ إضافة مهمة جديدة', 'callback_data': f'add_camp_task_setup:{new_camp.id}'}],
                    [{'text': '🔖 عرض تفاصيل المعسكر', 'callback_data': f'camp_details_{new_camp.id}'}],
                    [{'text': '🔙 العودة لقائمة المعسكرات', 'callback_data': 'admin_camps'}]
                ]
                
                markup = {'inline_keyboard': keyboard}
                send_message(chat_id, success_message, markup)
                
                # حذف بيانات الإنشاء المؤقتة
                del camp_creation_data[user_id]
                if user_id in private_setup_states:
                    del private_setup_states[user_id]
                
                return True
            else:
                # فشل في إنشاء المعسكر
                answer_callback_query(callback_query_id, "❌ فشل في إنشاء المعسكر. يرجى المحاولة مرة أخرى.")
                return False
                
        except Exception as e:
            logger.error(f"خطأ في إنشاء المعسكر: {e}")
            answer_callback_query(callback_query_id, "❌ حدث خطأ أثناء إنشاء المعسكر.")
            return False
            
    except Exception as e:
        logger.error(f"خطأ في تأكيد إنشاء المعسكر: {e}")
        answer_callback_query(callback_query_id, "❌ حدث خطأ أثناء معالجة طلبك")
        return False


def handle_group_settings(user_id, chat_id, group_telegram_id):
    """إدارة إعدادات مجموعة محددة"""
    try:
        # الحصول على معلومات المجموعة
        group = Group.query.filter_by(telegram_id=group_telegram_id, is_active=True).first()
        if not group:
            send_message(chat_id, "❗ لم يتم العثور على المجموعة المطلوبة أو أنها غير نشطة.")
            return False
        
        # التحقق من أن المستخدم هو مشرف المجموعة
        if group.admin_id != user_id:
            send_message(chat_id, "❗ أنت لست مشرفًا على هذه المجموعة.")
            return False
        
        # عرض إعدادات المجموعة
        keyboard = [
            [{'text': '🏝️ معسكرات المجموعة', 'callback_data': f'group_camps:{group.id}'}],
            [{'text': '➕ إنشاء معسكر جديد', 'callback_data': f'create_camp_setup:{group.id}'}],
            [{'text': '📅 إعدادات الجدول', 'callback_data': f'set_schedule_type:{group.id}'}],
            [{'text': '📣 تفعيل/إيقاف الرسائل التحفيزية', 'callback_data': f'toggle_motivation:{group.id}'}],
            [{'text': '📥 العودة لقائمة المجموعات', 'callback_data': 'admin_groups'}]
        ]
        
        # إرسال رسالة الإعدادات
        settings_message = f"""⚙️ <b>إعدادات المجموعة</b>: {group.title}
        
<b>الحالة:</b> {'نشطة ✅' if group.is_active else 'غير نشطة ❌'}
<b>نوع الجدول:</b> {group.schedule_type or 'غير محدد'}
<b>الرسائل التحفيزية:</b> {'مفعلة ✅' if group.motivation_enabled else 'غير مفعلة ❌'}

اختر إجراءً لإدارة هذه المجموعة:
"""
        
        markup = {'inline_keyboard': keyboard}
        send_message(chat_id, settings_message, markup)
        return True
    except Exception as e:
        logger.error(f"خطأ في عرض إعدادات المجموعة: {e}")
        send_message(chat_id, "❗ حدث خطأ أثناء محاولة عرض إعدادات المجموعة. يرجى المحاولة مرة أخرى لاحقًا.")
        return False


def handle_camp_details(user_id, chat_id, camp_id):
    """عرض تفاصيل معسكر محدد"""
    try:
        # الحصول على معلومات المعسكر
        camp = CustomCamp.query.get(camp_id)
        if not camp or not camp.is_active:
            send_message(chat_id, "❗ لم يتم العثور على المعسكر المطلوب أو أنه غير نشط.")
            return False
        
        # الحصول على معلومات المجموعة
        group = Group.query.get(camp.group_id)
        if not group:
            send_message(chat_id, "❗ لم يتم العثور على المجموعة المرتبطة بهذا المعسكر.")
            return False
        
        # التحقق من أن المستخدم هو مشرف المجموعة
        if group.admin_id != user_id:
            send_message(chat_id, "❗ أنت لست مشرفًا على المجموعة المرتبطة بهذا المعسكر.")
            return False
        
        # عدد المشاركين النشطين
        active_participants = CampParticipant.query.filter_by(camp_id=camp.id, is_active=True).count()
        
        # عدد المهام
        tasks_count = CampTask.query.filter_by(camp_id=camp.id).count()
        
        # تنسيق التواريخ
        start_date_str = camp.start_date.strftime('%Y-%m-%d')
        end_date_str = camp.end_date.strftime('%Y-%m-%d')
        
        # عرض تفاصيل المعسكر
        camp_details = f"""🏝️ <b>معسكر دراسي:</b> {camp.name}
        
<b>المجموعة:</b> {group.title}
<b>الوصف:</b> {camp.description}
<b>الفترة:</b> من {start_date_str} إلى {end_date_str}
<b>المشاركون:</b> {active_participants} """
        
        if camp.max_participants > 0:
            camp_details += f"/ {camp.max_participants}"
            
        camp_details += f"\n<b>عدد المهام:</b> {tasks_count}\n"
        
        # أزرار إدارة المعسكر
        keyboard = [
            [{'text': '📝 إضافة مهمة جديدة', 'callback_data': f'add_camp_task_setup:{camp.id}'}],
            [{'text': '👥 عرض المشاركين', 'callback_data': f'view_camp_participants:{camp.id}'}],
            [{'text': '📃 عرض المهام', 'callback_data': f'view_camp_tasks:{camp.id}'}],
            [{'text': '📊 تقرير المعسكر', 'callback_data': f'camp_report:{camp.id}'}],
            [{'text': '❌ إيقاف المعسكر', 'callback_data': f'deactivate_camp:{camp.id}'}],
            [{'text': '📥 العودة لقائمة المعسكرات', 'callback_data': 'admin_camps'}]
        ]
        
        markup = {'inline_keyboard': keyboard}
        send_message(chat_id, camp_details, markup)
        return True
    except Exception as e:
        logger.error(f"خطأ في عرض تفاصيل المعسكر: {e}")
        send_message(chat_id, "❗ حدث خطأ أثناء محاولة عرض تفاصيل المعسكر. يرجى المحاولة مرة أخرى لاحقًا.")
        return False


def handle_group_camps(user_id, chat_id, group_id):
    """عرض معسكرات مجموعة محددة"""
    try:
        # التحقق من وجود المجموعة
        group = Group.query.get(group_id)
        if not group or not group.is_active:
            send_message(chat_id, "❌ لم يتم العثور على المجموعة المطلوبة أو أنها غير نشطة.")
            return False
            
        # التحقق من أن المستخدم هو مشرف المجموعة
        if group.admin_id != user_id:
            send_message(chat_id, "❌ أنت لست مشرفًا على هذه المجموعة.")
            return False
            
        # الحصول على معسكرات المجموعة
        active_camps = CustomCamp.query.filter_by(group_id=group_id, is_active=True).all()
        inactive_camps = CustomCamp.query.filter_by(group_id=group_id, is_active=False).all()
        
        # إنشاء رسالة المعسكرات
        message = f"""🏝️ <b>معسكرات مجموعة:</b> {group.title}

"""
        
        # إنشاء لوحة المفاتيح
        keyboard = []
        
        # إضافة المعسكرات النشطة
        if active_camps:
            message += f"<b>المعسكرات النشطة:</b> ({len(active_camps)})✅\n\n"
            for camp in active_camps:
                # تنسيق تاريخ البدء والنهاية
                start_date_str = camp.start_date.strftime('%Y-%m-%d')
                end_date_str = camp.end_date.strftime('%Y-%m-%d')
                
                # عدد المشاركين النشطين
                active_participants = CampParticipant.query.filter_by(camp_id=camp.id, is_active=True).count()
                
                # عدد المهام
                tasks_count = CampTask.query.filter_by(camp_id=camp.id).count()
                
                message += f"\U0001F3D5 <b>{camp.name}</b>\n"
                message += f"\u2022 الفترة: {start_date_str} - {end_date_str}\n"
                message += f"\u2022 المشاركون: {active_participants}"
                if camp.max_participants > 0:
                    message += f" / {camp.max_participants}"
                message += f"\n\u2022 المهام: {tasks_count}\n\n"
                
                # إضافة زر لعرض تفاصيل هذا المعسكر
                keyboard.append([{'text': f'🗒️ {camp.name}', 'callback_data': f'camp_details_{camp.id}'}])
        else:
            message += "<i>لا يوجد معسكرات نشطة لهذه المجموعة.</i>\n\n"
            
        # إضافة زر لإنشاء معسكر جديد
        keyboard.append([{'text': '➕ إنشاء معسكر جديد', 'callback_data': f'create_camp_setup:{group_id}'}])
        
        # إضافة زر للعودة إلى إعدادات المجموعة
        keyboard.append([{'text': '🔙 العودة لإعدادات المجموعة', 'callback_data': f'group_setup_{group.telegram_id}'}])
        
        # إضافة زر للعودة إلى قائمة المجموعات
        keyboard.append([{'text': '🔙 العودة لقائمة المجموعات', 'callback_data': 'admin_groups'}])
        
        # إرسال الرسالة مع الأزرار
        markup = {'inline_keyboard': keyboard}
        send_message(chat_id, message, markup)
        return True
        
    except Exception as e:
        logger.error(f"خطأ في عرض معسكرات المجموعة: {e}")
        send_message(chat_id, "❌ حدث خطأ أثناء محاولة عرض معسكرات المجموعة. يرجى المحاولة مرة أخرى.")
        return False
        

def process_camp_creation_input(user_id, chat_id, text, current_state):
    """معالجة إدخال بيانات إنشاء المعسكر"""
    try:
        # التحقق من وجود البيانات
        if user_id not in camp_creation_data:
            # إذا لم تكن هناك بيانات، إعادة المستخدم للقائمة الرئيسية
            send_message(chat_id, "❗ حدث خطأ في عملية إنشاء المعسكر. الرجاء المحاولة مرة أخرى.")
            from study_bot.bot import show_main_menu
            show_main_menu(chat_id)
            return False
        
        # معالجة الإدخال بناءً على الحالة الحالية
        if current_state == 'waiting_camp_name':
            # تخزين اسم المعسكر
            camp_creation_data[user_id]['name'] = text.strip()
            camp_creation_data[user_id]['step'] = 2  # خطوة إدخال الوصف
            
            # الانتقال إلى الخطوة التالية: وصف المعسكر
            message = f"""🏝️ <b>إنشاء معسكر جديد</b> - الخطوة 2/5

<b>الاسم:</b> {camp_creation_data[user_id]['name']}

الرجاء إرسال وصف المعسكر الدراسي.
(مثل: معسكر تحفيزي للطلاب المتفوقين لتحقيق أعلى الدرجات)

يمكنك إلغاء العملية بأي وقت بالضغط على زر الإلغاء أدناه.
"""
            
            # إنشاء زر الإلغاء
            keyboard = [
                [{'text': '❌ إلغاء إنشاء المعسكر', 'callback_data': 'camp_create_cancel'}]
            ]
            
            markup = {'inline_keyboard': keyboard}
            send_message(chat_id, message, markup)
            
            # تعيين حالة المستخدم لاستقبال وصف المعسكر
            private_setup_states[user_id] = 'waiting_camp_description'
            
        elif current_state == 'waiting_camp_description':
            # تخزين وصف المعسكر
            camp_creation_data[user_id]['description'] = text.strip()
            camp_creation_data[user_id]['step'] = 3  # خطوة إدخال تاريخ البداية
            
            # الانتقال إلى الخطوة التالية: تاريخ البداية
            message = f"""🏝️ <b>إنشاء معسكر جديد</b> - الخطوة 3/5

<b>الاسم:</b> {camp_creation_data[user_id]['name']}
<b>الوصف:</b> {camp_creation_data[user_id]['description']}

الرجاء إرسال تاريخ بداية المعسكر بالصيغة: YYYY-MM-DD
(مثل: 2025-05-15)

يمكنك إلغاء العملية بأي وقت بالضغط على زر الإلغاء أدناه.
"""
            
            # إنشاء زر الإلغاء
            keyboard = [
                [{'text': '❌ إلغاء إنشاء المعسكر', 'callback_data': 'camp_create_cancel'}]
            ]
            
            markup = {'inline_keyboard': keyboard}
            send_message(chat_id, message, markup)
            
            # تعيين حالة المستخدم لاستقبال تاريخ البداية
            private_setup_states[user_id] = 'waiting_camp_start_date'
            
        elif current_state == 'waiting_camp_start_date':
            # التحقق من صحة تنسيق التاريخ
            try:
                start_date = datetime.strptime(text.strip(), '%Y-%m-%d')
                # تخزين تاريخ البداية
                camp_creation_data[user_id]['start_date'] = start_date
                camp_creation_data[user_id]['step'] = 4  # خطوة إدخال تاريخ النهاية
                
                # الانتقال إلى الخطوة التالية: تاريخ النهاية
                message = f"""🏝️ <b>إنشاء معسكر جديد</b> - الخطوة 4/5

<b>الاسم:</b> {camp_creation_data[user_id]['name']}
<b>الوصف:</b> {camp_creation_data[user_id]['description']}
<b>تاريخ البداية:</b> {start_date.strftime('%Y-%m-%d')}

الرجاء إرسال تاريخ نهاية المعسكر بالصيغة: YYYY-MM-DD
(مثل: 2025-06-15)

يمكنك إلغاء العملية بأي وقت بالضغط على زر الإلغاء أدناه.
"""
                
                # إنشاء زر الإلغاء
                keyboard = [
                    [{'text': '❌ إلغاء إنشاء المعسكر', 'callback_data': 'camp_create_cancel'}]
                ]
                
                markup = {'inline_keyboard': keyboard}
                send_message(chat_id, message, markup)
                
                # تعيين حالة المستخدم لاستقبال تاريخ النهاية
                private_setup_states[user_id] = 'waiting_camp_end_date'
            except ValueError:
                # تنسيق التاريخ غير صحيح
                send_message(chat_id, "❗ صيغة التاريخ غير صحيحة. الرجاء استخدام الصيغة: YYYY-MM-DD\nمثل: 2025-05-15")
                # إعادة طلب التاريخ مرة أخرى
            
        elif current_state == 'waiting_camp_end_date':
            # التحقق من صحة تنسيق التاريخ
            try:
                end_date = datetime.strptime(text.strip(), '%Y-%m-%d')
                start_date = camp_creation_data[user_id]['start_date']
                
                # التحقق من أن تاريخ النهاية بعد تاريخ البداية
                if end_date <= start_date:
                    send_message(chat_id, "❗ تاريخ النهاية يجب أن يكون بعد تاريخ البداية")
                    return True
                
                # تخزين تاريخ النهاية
                camp_creation_data[user_id]['end_date'] = end_date
                camp_creation_data[user_id]['step'] = 5  # خطوة إدخال الحد الأقصى للمشاركين
                
                # الانتقال إلى الخطوة التالية: الحد الأقصى للمشاركين
                message = f"""🏝️ <b>إنشاء معسكر جديد</b> - الخطوة 5/5

<b>الاسم:</b> {camp_creation_data[user_id]['name']}
<b>الوصف:</b> {camp_creation_data[user_id]['description']}
<b>تاريخ البداية:</b> {start_date.strftime('%Y-%m-%d')}
<b>تاريخ النهاية:</b> {end_date.strftime('%Y-%m-%d')}

الرجاء إرسال الحد الأقصى لعدد المشاركين (أرسل 0 للعدد غير محدود).

يمكنك إلغاء العملية بأي وقت بالضغط على زر الإلغاء أدناه.
"""
                
                # إنشاء زر الإلغاء
                keyboard = [
                    [{'text': '❌ إلغاء إنشاء المعسكر', 'callback_data': 'camp_create_cancel'}]
                ]
                
                markup = {'inline_keyboard': keyboard}
                send_message(chat_id, message, markup)
                
                # تعيين حالة المستخدم لاستقبال الحد الأقصى للمشاركين
                private_setup_states[user_id] = 'waiting_camp_max_participants'
            except ValueError:
                # تنسيق التاريخ غير صحيح
                send_message(chat_id, "❗ صيغة التاريخ غير صحيحة. الرجاء استخدام الصيغة: YYYY-MM-DD\nمثل: 2025-06-15")
                # إعادة طلب التاريخ مرة أخرى
            
        elif current_state == 'waiting_camp_max_participants':
            try:
                # التحقق من أن المدخل رقم
                max_participants = int(text.strip())
                if max_participants < 0:
                    send_message(chat_id, "❗ يجب أن يكون الحد الأقصى للمشاركين عددًا موجبًا أو صفرًا.")
                    return True
                
                # تخزين الحد الأقصى للمشاركين
                camp_creation_data[user_id]['max_participants'] = max_participants
                
                # عرض ملخص المعسكر وزر التأكيد
                message = f"""🏝️ <b>ملخص بيانات المعسكر</b>

<b>الاسم:</b> {camp_creation_data[user_id]['name']}
<b>الوصف:</b> {camp_creation_data[user_id]['description']}
<b>تاريخ البداية:</b> {camp_creation_data[user_id]['start_date'].strftime('%Y-%m-%d')}
<b>تاريخ النهاية:</b> {camp_creation_data[user_id]['end_date'].strftime('%Y-%m-%d')}
<b>الحد الأقصى للمشاركين:</b> {'غير محدود' if max_participants == 0 else max_participants}

هل ترغب في تأكيد إنشاء المعسكر بالمعلومات المذكورة أعلاه؟
"""
                
                # إنشاء أزرار التأكيد والإلغاء
                keyboard = [
                    [{'text': '✅ تأكيد إنشاء المعسكر', 'callback_data': 'camp_create_confirm'}],
                    [{'text': '❌ إلغاء إنشاء المعسكر', 'callback_data': 'camp_create_cancel'}]
                ]
                
                markup = {'inline_keyboard': keyboard}
                send_message(chat_id, message, markup)
                
                # إزالة حالة الإنشاء لأن الخطوة التالية ستكون عبر زر
                if user_id in private_setup_states:
                    del private_setup_states[user_id]
            except ValueError:
                # المدخل ليس رقمًا
                send_message(chat_id, "❗ الرجاء إدخال رقم صحيح للحد الأقصى للمشاركين (0 للعدد غير محدود).")
                # إعادة طلب الرقم مرة أخرى
        
        return True
    except Exception as e:
        logger.error(f"خطأ في معالجة إدخال بيانات المعسكر: {e}")
        send_message(chat_id, "❗ حدث خطأ أثناء معالجة مدخلاتك. الرجاء المحاولة مرة أخرى.")
        return False


def handle_admin_camps(user_id, chat_id, message_id=None):
    """إدارة المعسكرات كمشرف"""
    # التحقق من المجموعات التي يشرف عليها المستخدم
    admin_groups = Group.query.filter_by(admin_id=user_id, is_active=True).all()
    
    if not admin_groups:
        send_message(chat_id, "❗ أنت لست مشرفًا على أي مجموعة حاليًا. يجب أن تكون مشرفًا على مجموعة لإدارة المعسكرات.")
        return False

    # قائمة المعسكرات
    try:
        # الحصول على قائمة بمعرفات المجموعات التي يشرف عليها المستخدم
        admin_group_ids = [group.id for group in admin_groups]
        
        # الحصول على قائمة المعسكرات النشطة لهذه المجموعات
        camps = CustomCamp.query.filter(
            CustomCamp.group_id.in_(admin_group_ids),
            CustomCamp.is_active == True
        ).all()
        
        # إذا لم تكن هناك معسكرات
        if not camps:
            no_camps_message = """🏝️ <b>لا توجد معسكرات دراسية نشطة</b>
            
لم يتم إنشاء أي معسكر دراسي بعد للمجموعات التي تشرف عليها.

يمكنك إنشاء معسكر جديد باستخدام الأمر <code>/newcamp</code>.
"""
            keyboard = [
                [{'text': '➕ إنشاء معسكر جديد', 'callback_data': 'create_new_camp'}],
                [{'text': '📥 العودة للقائمة الرئيسية', 'callback_data': 'back_to_main'}]
            ]
            markup = {'inline_keyboard': keyboard}
            send_message(chat_id, no_camps_message, markup)
            return True
        
        # إذا كانت هناك معسكرات، عرضها
        keyboard = []
        for camp in camps:
            # إضافة زر لكل معسكر
            keyboard.append([{
                'text': f"{camp.name} (المجموعة: {camp.group.title})",
                'callback_data': f"camp_details_{camp.id}"
            }])
        
        # إضافة أزرار الإجراءات
        keyboard.append([{'text': '➕ إنشاء معسكر جديد', 'callback_data': 'create_new_camp'}])
        keyboard.append([{'text': '📥 العودة للقائمة الرئيسية', 'callback_data': 'back_to_main'}])
        
        markup = {'inline_keyboard': keyboard}
        camps_message = f"""🏝️ <b>إدارة المعسكرات الدراسية</b>
        
لديك {len(camps)} معسكر/معسكرات دراسية نشطة.
اختر معسكرًا لإدارته أو أنشئ معسكرًا جديدًا:
"""
        send_message(chat_id, camps_message, markup)
        return True
    except Exception as e:
        logger.error(f"خطأ في معالجة قائمة المعسكرات: {e}")
        send_message(chat_id, "❗ حدث خطأ أثناء محاولة استرجاع قائمة المعسكرات. يرجى المحاولة مرة أخرى لاحقًا.")
        return False
