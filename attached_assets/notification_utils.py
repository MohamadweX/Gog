#!/usr/bin/env python3
"""
وحدة وظائف الإشعارات
تحتوي على وظائف الإشعارات المشتركة بين مختلف وحدات البوت
"""

import json
import random
import uuid
from threading import Timer

from study_bot.config import logger, TELEGRAM_API_URL
from study_bot.bot import send_message

# قاموس لتخزين المؤقتات
activation_timers = {}

def schedule_confirmation_message(app, chat_id, is_group=False, user_id=None, delay_seconds=120):
    """
    جدولة رسالة تأكيد بعد فترة زمنية محددة (الافتراضي: دقيقتان)
    """
    try:
        # إنشاء معرف فريد للمؤقت
        timer_id = str(uuid.uuid4())
        
        def send_confirmation_message():
            try:
                # إختيار رسالة تحفيزية عشوائية
                from study_bot.group_tasks import MOTIVATIONAL_QUOTES
                quote = random.choice(MOTIVATIONAL_QUOTES)
                
                # إضافة نص التأكيد
                confirmation_message = f"✅ <b>تأكيد التفعيل</b>\n\nتم تفعيل بوت الدراسة والتحفيز بنجاح.\n\n{quote}\n\n<i>فريق المطورين - @M_o_h_a_m_e_d_501</i>"
                
                # إرسال الرسالة
                send_message(chat_id, confirmation_message)
                
                logger.info(f"تم إرسال رسالة تأكيد التفعيل إلى {chat_id}")
                
                # إذا كانت المجموعة، أرسل رسالة للمشرف في الخاص
                if is_group and user_id:
                    send_admin_private_message(chat_id, user_id)
                
                # إزالة المؤقت من القاموس
                if timer_id in activation_timers:
                    del activation_timers[timer_id]
            except Exception as e:
                logger.error(f"خطأ في إرسال رسالة تأكيد التفعيل: {e}")
        
        # إنشاء مؤقت لإرسال الرسالة بعد المدة المحددة
        timer = Timer(delay_seconds, send_confirmation_message)
        timer.daemon = True  # جعل المؤقت خلفي لإيقافه عند إيقاف التطبيق
        timer.start()
        
        # تخزين المؤقت للرجوع إليه لاحقًا
        activation_timers[timer_id] = timer
        
        logger.info(f"تم جدولة رسالة تأكيد التفعيل لـ {chat_id} بعد {delay_seconds} ثانية")
        return timer_id
    except Exception as e:
        logger.error(f"خطأ في جدولة رسالة تأكيد التفعيل: {e}")
        return None

def send_admin_private_message(group_id, admin_id, app=None):
    """
    إرسال رسالة للمشرف في الخاص بعد تفعيل البوت في مجموعة
    ملاحظة: معامل app مطلوب للتوافق ولكنه غير مستخدم
    """
    try:
        # استيراد النماذج
        from study_bot.models import Group, User
        
        # الحصول على معلومات المجموعة
        group = Group.query.filter_by(telegram_id=group_id).first()
        if not group:
            # محاولة جلب المجموعة بالمعرف الرقمي
            group = Group.query.filter_by(id=group_id).first()
            if not group:
                logger.error(f"لم يتم العثور على المجموعة بالمعرف {group_id}")
                return False
        
        # التحقق من وجود المستخدم
        user = User.query.filter_by(telegram_id=admin_id).first()
        if not user:
            # إنشاء مستخدم جديد إذا لم يكن موجودًا
            user = User.get_or_create(telegram_id=admin_id)
        
        # إرسال رسالة للمشرف في الخاص
        group_name = group.title if group.title else f"مجموعة {group_id}"
        admin_message = f"""🛠️ <b>إدارة المجموعة</b>

مرحبًا! أنت الآن مشرف لمجموعة <b>{group_name}</b> في بوت الدراسة والتحفيز.

يمكنك إدارة المجموعة وإعداد المعسكرات الدراسية مباشرة من المحادثة الخاصة معي هنا.

<b>الأوامر الرئيسية:</b>
/groups - لإدارة مجموعاتك وإعداداتها
/camps - لإنشاء وإدارة معسكرات الدراسة المخصصة
/newcamp - لإنشاء معسكر دراسي جديد بجدول ومهام مخصصة
/customcamp - لتخصيص معسكر دراسي موجود
/schedule - لإدارة جداول المجموعة (صباحي/مسائي/مخصص)
/grouphelp - لعرض مساعدة مفصلة حول إدارة المجموعة

<b>ملاحظة هامة:</b> جميع إعدادات المعسكرات والجداول يمكن ضبطها من هنا في الخاص دون الحاجة لازعاج مجموعتك برسائل الإعداد.

<i>للمساعدة أرسل /help أو تواصل مع فريق الدعم: @M_o_h_a_m_e_d_501</i>"""
        
        send_message(admin_id, admin_message)
        logger.info(f"تم إرسال رسالة خاصة للمشرف {admin_id} عن المجموعة {group_name}")
        return True
    except Exception as e:
        logger.error(f"خطأ في إرسال رسالة للمشرف في الخاص: {e}")
        return False
