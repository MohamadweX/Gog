"""
إدارة المعسكرات من المحادثات الخاصة
يحتوي على وظائف للتعامل مع إعدادات المعسكرات من المحادثة الخاصة بمشرف المجموعة
"""

import json
import random
import traceback
from datetime import datetime, timedelta

from study_bot.config import logger
from study_bot.models import db

# ملف تخزين حالة الإعدادات المؤقتة
_private_setup_states = {}

# مخزن مؤقت لبيانات إنشاء المعسكر
_camp_creation_data = {}

def handle_admin_groups(user_id, chat_id, message_id=None):
    """إدارة المجموعات كمشرف"""
    try:
        # التحقق من المجموعات التي يشرف عليها المستخدم
        from study_bot.models import Group
        from study_bot.bot import send_message
        
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
    except Exception as e:
        logger.error(f"خطأ في إدارة المجموعات كمشرف: {e}")
        logger.error(traceback.format_exc())
        return False


def handle_admin_camps(user_id, chat_id):
    """إدارة معسكرات الدراسة كمشرف"""
    try:
        # التحقق من المجموعات التي يشرف عليها المستخدم
        from study_bot.models import Group, CustomCamp
        from study_bot.bot import send_message
        
        admin_groups = Group.query.filter_by(admin_id=user_id, is_active=True).all()
        
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
    except Exception as e:
        logger.error(f"خطأ في إدارة معسكرات الدراسة كمشرف: {e}")
        logger.error(traceback.format_exc())
        return False


def handle_create_new_camp(user_id, chat_id):
    """معالجة طلب إنشاء معسكر جديد"""
    try:
        from study_bot.models import Group
        from study_bot.bot import send_message
        
        # التحقق من المجموعات التي يشرف عليها المستخدم
        admin_groups = Group.query.filter_by(admin_id=user_id, is_active=True).all()
        
        if not admin_groups:
            send_message(chat_id, "❗ أنت لست مشرفًا على أي مجموعة حاليًا. يجب أن تكون مشرفًا على مجموعة لإنشاء معسكر.")
            return False
        
        # إنشاء لوحة مفاتيح لاختيار المجموعة
        keyboard = []
        for group in admin_groups:
            keyboard.append([{
                'text': f"{group.title}",
                'callback_data': f"new_camp_group:{group.id}"
            }])
        
        # إضافة زر إلغاء
        keyboard.append([{'text': '❌ إلغاء', 'callback_data': 'cancel_camp_creation'}])
        
        # إرسال رسالة اختيار المجموعة
        message = """🏝️ <b>إنشاء معسكر دراسي جديد</b>
        
الخطوة 1: اختر المجموعة التي ستنشئ فيها المعسكر:
"""
        
        markup = {'inline_keyboard': keyboard}
        send_message(chat_id, message, markup)
        
        # تخزين حالة الإنشاء
        _private_setup_states[user_id] = {'state': 'selecting_group_for_camp'}
        
        return True
    except Exception as e:
        logger.error(f"خطأ في معالجة طلب إنشاء معسكر جديد: {e}")
        logger.error(traceback.format_exc())
        return False


def handle_private_camp_callbacks(callback_data, user_id, chat_id, callback_query_id):
    """معالجة الاستجابات للأزرار المتعلقة بالمعسكرات في المحادثة الخاصة"""
    try:
        from study_bot.models import Group, CustomCamp, CampTask
        from study_bot.bot import send_message
        from study_bot.group_handlers import answer_callback_query
        
        # معالجة زر العودة للقائمة الرئيسية
        if callback_data == 'back_to_main':
            # مسح حالة الإعداد
            if user_id in _private_setup_states:
                del _private_setup_states[user_id]
            
            # عرض القائمة الرئيسية
            from study_bot.bot import show_main_menu
            show_main_menu(chat_id)
            
            answer_callback_query(callback_query_id, "تم العودة للقائمة الرئيسية")
            return True
        
        # معالجة اختيار مجموعة لإنشاء معسكر
        elif callback_data.startswith('new_camp_group:'):
            group_id = int(callback_data.split(':')[1])
            
            # التحقق من المجموعة
            group = Group.query.get(group_id)
            if not group or not group.is_active:
                answer_callback_query(callback_query_id, "❌ المجموعة غير موجودة أو غير نشطة", True)
                return False
            
            # التحقق من أن المستخدم هو مشرف المجموعة
            if group.admin_id != user_id:
                answer_callback_query(callback_query_id, "❌ يجب أن تكون مشرف المجموعة لإنشاء معسكر", True)
                return False
            
            # تخزين معرف المجموعة في بيانات الإنشاء
            _camp_creation_data[user_id] = {'group_id': group_id}
            
            # تحديث حالة الإعداد
            _private_setup_states[user_id] = {'state': 'entering_camp_name'}
            
            # إرسال رسالة إدخال اسم المعسكر
            message = f"""🏝️ <b>إنشاء معسكر دراسي جديد</b>
            
المجموعة المختارة: <b>{group.title}</b>

الخطوة 2: أدخل اسم المعسكر (مثال: معسكر الرياضيات، معسكر اللغة العربية):
"""
            
            send_message(chat_id, message)
            answer_callback_query(callback_query_id, f"تم اختيار مجموعة {group.title}")
            return True
        
        # معالجة إلغاء إنشاء المعسكر
        elif callback_data == 'cancel_camp_creation':
            # مسح حالة الإعداد وبيانات الإنشاء
            if user_id in _private_setup_states:
                del _private_setup_states[user_id]
            
            if user_id in _camp_creation_data:
                del _camp_creation_data[user_id]
            
            # إرسال رسالة تأكيد الإلغاء
            message = """❌ <b>تم إلغاء إنشاء المعسكر</b>
            
يمكنك إنشاء معسكر جديد في أي وقت من قائمة إدارة المعسكرات.
"""
            
            send_message(chat_id, message)
            answer_callback_query(callback_query_id, "تم إلغاء إنشاء المعسكر")
            
            # العودة لقائمة إدارة المعسكرات
            handle_admin_camps(user_id, chat_id)
            
            return True
        
        # معالجة اختيار معسكر للإدارة
        elif callback_data.startswith('manage_camp:'):
            camp_id = int(callback_data.split(':')[1])
            
            # التحقق من المعسكر
            camp = CustomCamp.query.get(camp_id)
            if not camp or not camp.is_active:
                answer_callback_query(callback_query_id, "❌ المعسكر غير موجود أو غير نشط", True)
                return False
            
            # التحقق من أن المستخدم هو مشرف المجموعة
            group = Group.query.get(camp.group_id)
            if not group or group.admin_id != user_id:
                answer_callback_query(callback_query_id, "❌ يجب أن تكون مشرف المجموعة لإدارة المعسكر", True)
                return False
            
            # إنشاء لوحة مفاتيح لإدارة المعسكر
            keyboard = []
            
            # إضافة أزرار الإدارة
            keyboard.append([{'text': '➕ إضافة مهمة جديدة', 'callback_data': f"add_task_to_camp:{camp_id}"}])
            keyboard.append([{'text': '📊 عرض تقرير المعسكر', 'callback_data': f"view_camp_report:{camp_id}"}])
            keyboard.append([{'text': '❌ إنهاء المعسكر', 'callback_data': f"end_camp:{camp_id}"}])
            keyboard.append([{'text': '🔙 رجوع لقائمة المعسكرات', 'callback_data': 'back_to_camps'}])
            
            # الحصول على مهام المعسكر
            tasks = CampTask.query.filter_by(camp_id=camp.id).order_by(CampTask.scheduled_time).all()
            
            # إعداد الرسالة
            message = f"""🏝️ <b>إدارة معسكر: {camp.name}</b>
            
<b>المجموعة:</b> {group.title}
<b>تاريخ البدء:</b> {camp.start_date.strftime('%Y-%m-%d %H:%M')}
<b>تاريخ الانتهاء:</b> {camp.end_date.strftime('%Y-%m-%d %H:%M')}
<b>عدد المهام:</b> {len(tasks)}
"""
            
            # إضافة المهام القادمة
            now = datetime.utcnow()
            upcoming_tasks = [task for task in tasks if task.scheduled_time > now and not task.is_sent]
            if upcoming_tasks:
                message += "\n<b>المهام القادمة:</b>\n"
                for i, task in enumerate(upcoming_tasks[:5]):  # عرض أول 5 مهام فقط
                    message += f"{i+1}. {task.title} ({task.scheduled_time.strftime('%Y-%m-%d %H:%M')})\n"
            
            # إرسال الرسالة مع لوحة المفاتيح
            markup = {'inline_keyboard': keyboard}
            send_message(chat_id, message, markup)
            answer_callback_query(callback_query_id, f"تم عرض إدارة معسكر {camp.name}")
            return True
        
        # معالجة العودة لقائمة المعسكرات
        elif callback_data == 'back_to_camps':
            handle_admin_camps(user_id, chat_id)
            answer_callback_query(callback_query_id, "تم العودة لقائمة المعسكرات")
            return True
        
        # معالجة طلب إنشاء معسكر جديد
        elif callback_data == 'create_new_camp':
            handle_create_new_camp(user_id, chat_id)
            answer_callback_query(callback_query_id, "بدء إنشاء معسكر جديد")
            return True
        
        # معالجة طلب إضافة مهمة لمعسكر
        elif callback_data.startswith('add_task_to_camp:'):
            camp_id = int(callback_data.split(':')[1])
            
            # التحقق من المعسكر
            camp = CustomCamp.query.get(camp_id)
            if not camp or not camp.is_active:
                answer_callback_query(callback_query_id, "❌ المعسكر غير موجود أو غير نشط", True)
                return False
            
            # التحقق من أن المستخدم هو مشرف المجموعة
            group = Group.query.get(camp.group_id)
            if not group or group.admin_id != user_id:
                answer_callback_query(callback_query_id, "❌ يجب أن تكون مشرف المجموعة لإدارة المعسكر", True)
                return False
            
            # تخزين معرف المعسكر في بيانات الإنشاء
            _camp_creation_data[user_id] = {'camp_id': camp_id}
            
            # تحديث حالة الإعداد
            _private_setup_states[user_id] = {'state': 'entering_task_title'}
            
            # إرسال رسالة إدخال عنوان المهمة
            message = f"""➕ <b>إضافة مهمة جديدة</b>
            
المعسكر: <b>{camp.name}</b>

الخطوة 1: أدخل عنوان المهمة (مثال: مذاكرة الفصل الأول، حل تمارين الوحدة الثانية):
"""
            
            send_message(chat_id, message)
            answer_callback_query(callback_query_id, "بدء إضافة مهمة جديدة")
            return True
        
        # معالجة عرض تقرير المعسكر
        elif callback_data.startswith('view_camp_report:'):
            camp_id = int(callback_data.split(':')[1])
            
            # التحقق من المعسكر
            camp = CustomCamp.query.get(camp_id)
            if not camp or not camp.is_active:
                answer_callback_query(callback_query_id, "❌ المعسكر غير موجود أو غير نشط", True)
                return False
            
            # التحقق من أن المستخدم هو مشرف المجموعة
            group = Group.query.get(camp.group_id)
            if not group or group.admin_id != user_id:
                answer_callback_query(callback_query_id, "❌ يجب أن تكون مشرف المجموعة لإدارة المعسكر", True)
                return False
            
            # طلب تقرير المعسكر
            from study_bot.camp_scheduler import send_camp_daily_report
            result = send_camp_daily_report(camp_id)
            
            if result:
                answer_callback_query(callback_query_id, "✅ تم إرسال تقرير المعسكر للمجموعة", True)
            else:
                answer_callback_query(callback_query_id, "❌ فشل إرسال تقرير المعسكر", True)
            
            return True
        
        # معالجة إنهاء المعسكر
        elif callback_data.startswith('end_camp:'):
            camp_id = int(callback_data.split(':')[1])
            
            # التحقق من المعسكر
            camp = CustomCamp.query.get(camp_id)
            if not camp or not camp.is_active:
                answer_callback_query(callback_query_id, "❌ المعسكر غير موجود أو غير نشط", True)
                return False
            
            # التحقق من أن المستخدم هو مشرف المجموعة
            group = Group.query.get(camp.group_id)
            if not group or group.admin_id != user_id:
                answer_callback_query(callback_query_id, "❌ يجب أن تكون مشرف المجموعة لإدارة المعسكر", True)
                return False
            
            # إنشاء لوحة مفاتيح لتأكيد إنهاء المعسكر
            keyboard = [
                [{'text': '✅ نعم، إنهاء المعسكر', 'callback_data': f"confirm_end_camp:{camp_id}"}],
                [{'text': '❌ لا، إلغاء', 'callback_data': f"manage_camp:{camp_id}"}]
            ]
            
            # إرسال رسالة تأكيد إنهاء المعسكر
            message = f"""⚠️ <b>تأكيد إنهاء المعسكر</b>
            
هل أنت متأكد من إنهاء معسكر "{camp.name}"؟

سيتم تغيير حالة المعسكر إلى "غير نشط" ولن يتم إرسال أي مهام جديدة.
ستبقى بيانات المعسكر والمشاركين في قاعدة البيانات لإعداد التقارير.
"""
            
            markup = {'inline_keyboard': keyboard}
            send_message(chat_id, message, markup)
            answer_callback_query(callback_query_id, "تأكيد إنهاء المعسكر")
            return True
        
        # معالجة تأكيد إنهاء المعسكر
        elif callback_data.startswith('confirm_end_camp:'):
            camp_id = int(callback_data.split(':')[1])
            
            # التحقق من المعسكر
            camp = CustomCamp.query.get(camp_id)
            if not camp or not camp.is_active:
                answer_callback_query(callback_query_id, "❌ المعسكر غير موجود أو غير نشط", True)
                return False
            
            # التحقق من أن المستخدم هو مشرف المجموعة
            group = Group.query.get(camp.group_id)
            if not group or group.admin_id != user_id:
                answer_callback_query(callback_query_id, "❌ يجب أن تكون مشرف المجموعة لإدارة المعسكر", True)
                return False
            
            # تغيير حالة المعسكر إلى غير نشط
            camp.is_active = False
            db.session.commit()
            
            # إرسال رسالة تأكيد الإنهاء
            message = f"""✅ <b>تم إنهاء المعسكر</b>
            
تم إنهاء معسكر "{camp.name}" بنجاح.

يمكنك إنشاء معسكر جديد من قائمة إدارة المعسكرات.
"""
            
            send_message(chat_id, message)
            answer_callback_query(callback_query_id, "تم إنهاء المعسكر بنجاح")
            
            # العودة لقائمة إدارة المعسكرات
            handle_admin_camps(user_id, chat_id)
            
            return True
        
        else:
            logger.warning(f"استجابة غير معروفة: {callback_data}")
            answer_callback_query(callback_query_id, "❌ طلب غير معروف", True)
            return False
    except Exception as e:
        logger.error(f"خطأ في معالجة الاستجابات للأزرار المتعلقة بالمعسكرات في المحادثة الخاصة: {e}")
        logger.error(traceback.format_exc())
        answer_callback_query(callback_query_id, "❌ حدث خطأ أثناء معالجة الطلب", True)
        return False


def handle_private_camp_message(message_text, user_id, chat_id):
    """معالجة الرسائل المتعلقة بإعداد المعسكرات في المحادثة الخاصة"""
    try:
        from study_bot.bot import send_message
        
        # التحقق من وجود حالة إعداد للمستخدم
        if user_id not in _private_setup_states:
            return False
        
        state = _private_setup_states[user_id]['state']
        
        # معالجة إدخال اسم المعسكر
        if state == 'entering_camp_name':
            # التحقق من صحة الاسم
            camp_name = message_text.strip()
            if not camp_name or len(camp_name) < 3:
                send_message(chat_id, "❌ اسم المعسكر قصير جدًا. يجب أن يكون 3 أحرف على الأقل.")
                return True
            
            # تخزين اسم المعسكر في بيانات الإنشاء
            _camp_creation_data[user_id]['camp_name'] = camp_name
            
            # تحديث الحالة
            _private_setup_states[user_id]['state'] = 'entering_camp_description'
            
            # طلب وصف المعسكر
            message = f"""🏝️ <b>إنشاء معسكر دراسي جديد</b>
            
الاسم: <b>{camp_name}</b>

الخطوة 3: أدخل وصف المعسكر (مثال: معسكر مكثف لمراجعة مادة الرياضيات للاختبار النهائي):
"""
            
            send_message(chat_id, message)
            return True
        
        # معالجة إدخال وصف المعسكر
        elif state == 'entering_camp_description':
            # التحقق من صحة الوصف
            camp_description = message_text.strip()
            
            # تخزين وصف المعسكر في بيانات الإنشاء
            _camp_creation_data[user_id]['camp_description'] = camp_description
            
            # تحديث الحالة
            _private_setup_states[user_id]['state'] = 'entering_camp_start_date'
            
            # طلب تاريخ بدء المعسكر
            message = f"""🏝️ <b>إنشاء معسكر دراسي جديد</b>
            
الاسم: <b>{_camp_creation_data[user_id]['camp_name']}</b>
الوصف: {camp_description}

الخطوة 4: أدخل تاريخ بدء المعسكر بالصيغة التالية:
YYYY-MM-DD HH:MM

مثال: 2025-05-10 08:00
"""
            
            send_message(chat_id, message)
            return True
        
        # معالجة إدخال تاريخ بدء المعسكر
        elif state == 'entering_camp_start_date':
            # التحقق من صحة التاريخ
            try:
                start_date = datetime.strptime(message_text.strip(), "%Y-%m-%d %H:%M")
            except ValueError:
                send_message(chat_id, """❌ صيغة التاريخ غير صحيحة.
                
يجب أن تكون الصيغة: YYYY-MM-DD HH:MM
مثال: 2025-05-10 08:00""")
                return True
            
            # التحقق من أن التاريخ في المستقبل
            if start_date <= datetime.utcnow():
                send_message(chat_id, "❌ تاريخ البدء يجب أن يكون في المستقبل.")
                return True
            
            # تخزين تاريخ البدء في بيانات الإنشاء
            _camp_creation_data[user_id]['start_date'] = start_date
            
            # تحديث الحالة
            _private_setup_states[user_id]['state'] = 'entering_camp_end_date'
            
            # طلب تاريخ انتهاء المعسكر
            message = f"""🏝️ <b>إنشاء معسكر دراسي جديد</b>
            
الاسم: <b>{_camp_creation_data[user_id]['camp_name']}</b>
تاريخ البدء: {start_date.strftime('%Y-%m-%d %H:%M')}

الخطوة 5: أدخل تاريخ انتهاء المعسكر بالصيغة التالية:
YYYY-MM-DD HH:MM

مثال: 2025-05-20 22:00
"""
            
            send_message(chat_id, message)
            return True
        
        # معالجة إدخال تاريخ انتهاء المعسكر
        elif state == 'entering_camp_end_date':
            # التحقق من صحة التاريخ
            try:
                end_date = datetime.strptime(message_text.strip(), "%Y-%m-%d %H:%M")
            except ValueError:
                send_message(chat_id, """❌ صيغة التاريخ غير صحيحة.
                
يجب أن تكون الصيغة: YYYY-MM-DD HH:MM
مثال: 2025-05-20 22:00""")
                return True
            
            # التحقق من أن تاريخ الانتهاء بعد تاريخ البدء
            if end_date <= _camp_creation_data[user_id]['start_date']:
                send_message(chat_id, "❌ تاريخ الانتهاء يجب أن يكون بعد تاريخ البدء.")
                return True
            
            # تخزين تاريخ الانتهاء في بيانات الإنشاء
            _camp_creation_data[user_id]['end_date'] = end_date
            
            # تحديث الحالة
            _private_setup_states[user_id]['state'] = 'entering_camp_max_participants'
            
            # طلب الحد الأقصى للمشاركين
            message = f"""🏝️ <b>إنشاء معسكر دراسي جديد</b>
            
الاسم: <b>{_camp_creation_data[user_id]['camp_name']}</b>
تاريخ البدء: {_camp_creation_data[user_id]['start_date'].strftime('%Y-%m-%d %H:%M')}
تاريخ الانتهاء: {end_date.strftime('%Y-%m-%d %H:%M')}

الخطوة 6: أدخل الحد الأقصى لعدد المشاركين (أدخل 0 للعدد غير المحدود):
"""
            
            send_message(chat_id, message)
            return True
        
        # معالجة إدخال الحد الأقصى للمشاركين
        elif state == 'entering_camp_max_participants':
            # التحقق من صحة العدد
            try:
                max_participants = int(message_text.strip())
                if max_participants < 0:
                    max_participants = 0
            except ValueError:
                send_message(chat_id, "❌ الرجاء إدخال رقم صحيح.")
                return True
            
            # تخزين الحد الأقصى للمشاركين في بيانات الإنشاء
            _camp_creation_data[user_id]['max_participants'] = max_participants
            
            # إنشاء المعسكر
            from study_bot.custom_camps import create_custom_camp
            
            camp = create_custom_camp(
                _camp_creation_data[user_id]['group_id'],
                user_id,
                _camp_creation_data[user_id]['camp_name'],
                _camp_creation_data[user_id]['camp_description'],
                _camp_creation_data[user_id]['start_date'],
                _camp_creation_data[user_id]['end_date'],
                max_participants
            )
            
            # تنظيف حالة الإعداد وبيانات الإنشاء
            del _private_setup_states[user_id]
            del _camp_creation_data[user_id]
            
            if camp:
                # إرسال رسالة تأكيد الإنشاء
                message = f"""✅ <b>تم إنشاء المعسكر بنجاح</b>
                
تم إنشاء معسكر "{camp.name}" بنجاح.

لإضافة مهام للمعسكر، استخدم الأمر /addtask في المجموعة بالصيغة التالية:
/addtask {camp.id} | عنوان المهمة | وصف المهمة | التاريخ والوقت | النقاط | المهلة بالدقائق

مثال:
/addtask {camp.id} | مذاكرة الفصل الأول | مراجعة الفصل الأول من كتاب الرياضيات | 2025-05-10 16:30 | 5 | 30
"""
                
                send_message(chat_id, message)
                
                # العودة لقائمة إدارة المعسكرات
                handle_admin_camps(user_id, chat_id)
            else:
                # إرسال رسالة فشل الإنشاء
                message = """❌ <b>فشل إنشاء المعسكر</b>
                
حدث خطأ أثناء إنشاء المعسكر. الرجاء المحاولة مرة أخرى.
"""
                
                send_message(chat_id, message)
            
            return True
        
        # معالجة إدخال عنوان المهمة
        elif state == 'entering_task_title':
            # التحقق من صحة العنوان
            task_title = message_text.strip()
            if not task_title or len(task_title) < 3:
                send_message(chat_id, "❌ عنوان المهمة قصير جدًا. يجب أن يكون 3 أحرف على الأقل.")
                return True
            
            # تخزين عنوان المهمة في بيانات الإنشاء
            _camp_creation_data[user_id]['task_title'] = task_title
            
            # تحديث الحالة
            _private_setup_states[user_id]['state'] = 'entering_task_description'
            
            # طلب وصف المهمة
            message = f"""➕ <b>إضافة مهمة جديدة</b>
            
عنوان المهمة: <b>{task_title}</b>

الخطوة 2: أدخل وصف المهمة (مثال: قراءة وفهم النظريات الأساسية في الفصل الأول):
"""
            
            send_message(chat_id, message)
            return True
        
        # معالجة إدخال وصف المهمة
        elif state == 'entering_task_description':
            # التحقق من صحة الوصف
            task_description = message_text.strip()
            
            # تخزين وصف المهمة في بيانات الإنشاء
            _camp_creation_data[user_id]['task_description'] = task_description
            
            # تحديث الحالة
            _private_setup_states[user_id]['state'] = 'entering_task_time'
            
            # طلب وقت المهمة
            message = f"""➕ <b>إضافة مهمة جديدة</b>
            
عنوان المهمة: <b>{_camp_creation_data[user_id]['task_title']}</b>
الوصف: {task_description}

الخطوة 3: أدخل وقت المهمة بالصيغة التالية:
YYYY-MM-DD HH:MM

مثال: 2025-05-10 16:30
"""
            
            send_message(chat_id, message)
            return True
        
        # معالجة إدخال وقت المهمة
        elif state == 'entering_task_time':
            # التحقق من صحة التاريخ
            try:
                task_time = datetime.strptime(message_text.strip(), "%Y-%m-%d %H:%M")
            except ValueError:
                send_message(chat_id, """❌ صيغة التاريخ غير صحيحة.
                
يجب أن تكون الصيغة: YYYY-MM-DD HH:MM
مثال: 2025-05-10 16:30""")
                return True
            
            # التحقق من المعسكر
            from study_bot.models import CustomCamp
            
            camp = CustomCamp.query.get(_camp_creation_data[user_id]['camp_id'])
            if not camp or not camp.is_active:
                send_message(chat_id, "❌ المعسكر غير موجود أو غير نشط.")
                del _private_setup_states[user_id]
                return True
            
            # التحقق من أن وقت المهمة يقع ضمن فترة المعسكر
            if task_time < camp.start_date or task_time > camp.end_date:
                send_message(chat_id, f"❌ وقت المهمة يجب أن يكون بين {camp.start_date.strftime('%Y-%m-%d %H:%M')} و {camp.end_date.strftime('%Y-%m-%d %H:%M')}.")
                return True
            
            # تخزين وقت المهمة في بيانات الإنشاء
            _camp_creation_data[user_id]['task_time'] = task_time
            
            # تحديث الحالة
            _private_setup_states[user_id]['state'] = 'entering_task_points'
            
            # طلب نقاط المهمة
            message = f"""➕ <b>إضافة مهمة جديدة</b>
            
عنوان المهمة: <b>{_camp_creation_data[user_id]['task_title']}</b>
وقت المهمة: {task_time.strftime('%Y-%m-%d %H:%M')}

الخطوة 4: أدخل عدد النقاط للمهمة (رقم صحيح بين 1 و 10):
"""
            
            send_message(chat_id, message)
            return True
        
        # معالجة إدخال نقاط المهمة
        elif state == 'entering_task_points':
            # التحقق من صحة النقاط
            try:
                task_points = int(message_text.strip())
                if task_points < 1:
                    task_points = 1
                elif task_points > 10:
                    task_points = 10
            except ValueError:
                send_message(chat_id, "❌ الرجاء إدخال رقم صحيح بين 1 و 10.")
                return True
            
            # تخزين نقاط المهمة في بيانات الإنشاء
            _camp_creation_data[user_id]['task_points'] = task_points
            
            # تحديث الحالة
            _private_setup_states[user_id]['state'] = 'entering_task_deadline'
            
            # طلب مهلة المهمة
            message = f"""➕ <b>إضافة مهمة جديدة</b>
            
عنوان المهمة: <b>{_camp_creation_data[user_id]['task_title']}</b>
وقت المهمة: {_camp_creation_data[user_id]['task_time'].strftime('%Y-%m-%d %H:%M')}
النقاط: {task_points}

الخطوة 5: أدخل مهلة إكمال المهمة بالدقائق (مثال: 30):
"""
            
            send_message(chat_id, message)
            return True
        
        # معالجة إدخال مهلة المهمة
        elif state == 'entering_task_deadline':
            # التحقق من صحة المهلة
            try:
                task_deadline = int(message_text.strip())
                if task_deadline < 1:
                    task_deadline = 1
            except ValueError:
                send_message(chat_id, "❌ الرجاء إدخال رقم صحيح أكبر من 0.")
                return True
            
            # تخزين مهلة المهمة في بيانات الإنشاء
            _camp_creation_data[user_id]['task_deadline'] = task_deadline
            
            # إضافة المهمة للمعسكر
            from study_bot.custom_camps import add_camp_task
            
            task = add_camp_task(
                _camp_creation_data[user_id]['camp_id'],
                user_id,
                _camp_creation_data[user_id]['task_title'],
                _camp_creation_data[user_id]['task_description'],
                _camp_creation_data[user_id]['task_time'],
                _camp_creation_data[user_id]['task_points'],
                task_deadline
            )
            
            # تنظيف حالة الإعداد وبيانات الإنشاء
            del _private_setup_states[user_id]
            
            if task:
                # إرسال رسالة تأكيد الإضافة
                message = f"""✅ <b>تمت إضافة المهمة بنجاح</b>
                
تمت إضافة مهمة "{task.title}" بنجاح.

سيتم إرسال المهمة تلقائيًا في الوقت المحدد: {task.scheduled_time.strftime('%Y-%m-%d %H:%M')}
"""
                
                send_message(chat_id, message)
                
                # عرض قائمة إدارة المعسكر مرة أخرى
                from study_bot.group_handlers import handle_group_callback
                
                # إعداد بيانات لاستدعاء معالج الاستجابة
                data = {
                    'chat_id': chat_id,
                    'user_id': user_id,
                    'callback_data': f"manage_camp:{_camp_creation_data[user_id]['camp_id']}",
                    'callback_query_id': None
                }
                
                handle_group_callback(data['callback_data'], data)
            else:
                # إرسال رسالة فشل الإضافة
                message = """❌ <b>فشل إضافة المهمة</b>
                
حدث خطأ أثناء إضافة المهمة. الرجاء المحاولة مرة أخرى.
"""
                
                send_message(chat_id, message)
            
            return True
        
        return False
    except Exception as e:
        logger.error(f"خطأ في معالجة الرسائل المتعلقة بإعداد المعسكرات في المحادثة الخاصة: {e}")
        logger.error(traceback.format_exc())
        from study_bot.bot import send_message
        send_message(chat_id, "❌ حدث خطأ أثناء معالجة الرسالة. الرجاء المحاولة مرة أخرى.")
        return True