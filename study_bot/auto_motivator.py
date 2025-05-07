#!/usr/bin/env python3
"""
وحدة الإرسال التلقائي للرسائل التحفيزية
تحتوي على وظائف لإرسال رسائل تحفيزية تلقائية بعد وقت محدد من تفعيل البوت
"""

import threading
import time
import random
from datetime import datetime

from study_bot.config import logger, MOTIVATIONAL_MESSAGES, get_current_time
from study_bot.models import db, User, Group
from study_bot.bot import send_message

# وقت التأخير بالثواني قبل إرسال الرسالة التحفيزية
ACTIVATION_MOTIVATION_DELAY = 60  # دقيقة واحدة


def send_activation_motivation():
    """إرسال رسالة تحفيزية لجميع المجموعات النشطة بعد تفعيل البوت"""
    try:
        logger.info("جدولة إرسال رسائل تحفيزية بعد التفعيل...")
        
        # انتظار الوقت المحدد
        time.sleep(ACTIVATION_MOTIVATION_DELAY)
        
        # الحصول على المجموعات النشطة
        groups = Group.query.filter_by(is_active=True).all()
        if not groups:
            logger.warning("لا توجد مجموعات نشطة لإرسال رسائل تحفيزية")
            return
        
        # إعداد الرسالة التحفيزية
        current_time = get_current_time()
        motivation_message = random.choice(MOTIVATIONAL_MESSAGES)
        message_text = f"""🌟 <b>تم تفعيل بوت الدراسة والتحفيز!</b> 🌟

{motivation_message}

🕒 <b>الوقت الحالي:</b> {current_time.strftime('%H:%M')}
📅 <b>التاريخ:</b> {current_time.strftime('%Y-%m-%d')}

استخدم أمر /help للحصول على قائمة الأوامر المتاحة.
"""
        
        sent_count = 0
        for group in groups:
            try:
                result = send_message(group.telegram_id, message_text)
                if result:
                    sent_count += 1
                    logger.info(f"تم إرسال رسالة تفعيل تحفيزية إلى المجموعة {group.title} (ID: {group.telegram_id})")
                else:
                    logger.error(f"فشل في إرسال رسالة تفعيل تحفيزية إلى المجموعة {group.title} (ID: {group.telegram_id})")
            except Exception as e:
                logger.error(f"خطأ أثناء إرسال رسالة تفعيل تحفيزية: {e}")
                continue
        
        logger.info(f"تم إرسال رسائل تفعيل تحفيزية إلى {sent_count} مجموعة من أصل {len(groups)} مجموعة نشطة")
        return True
    except Exception as e:
        logger.error(f"خطأ في دالة إرسال الرسائل التحفيزية بعد التفعيل: {e}")
        return False


def schedule_activation_motivation():
    """جدولة إرسال رسالة تحفيزية في سلسلة منفصلة"""
    motivation_thread = threading.Thread(target=send_activation_motivation)
    motivation_thread.daemon = True
    motivation_thread.start()
    return motivation_thread