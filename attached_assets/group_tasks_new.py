#!/usr/bin/env python3
"""
وحدة مهام المجموعات
تحتوي على وظائف للتعامل مع مهام المجموعات ذات المهلة الزمنية
تم تطويره ليشمل جداول صباحية ومسائية متكاملة
"""

import json
import random
from datetime import datetime, timedelta

from study_bot.config import TELEGRAM_API_URL, logger
from study_bot.models import (User, Group, GroupParticipant, 
                            GroupScheduleTracker, GroupTaskTracker,
                            GroupTaskParticipant, MotivationalMessage, db)
from study_bot.group_handlers import send_group_message, answer_callback_query

# تحفيزات إضافية للعرض مع المهام
MOTIVATIONAL_QUOTES = [
    "امضِ قدماً، حتى عندما تكون الخطوة صعبة والطريق طويلة.",
    "النجاح ليس نهائياً، والفشل ليس قاتلاً، الشجاعة للمواصلة هي ما يهم.",
    "المذاكرة اليوم تعني النجاح غداً.",
    "من تعب ساعة تنعم ألف ساعة.",
    "ليس المهم أن تبدأ بقوة، الأهم أن تستمر بعزيمة.",
    "العلم نور، والتركيز مفتاحه.",
    "الاستثمار في العلم يعطي أفضل الفوائد.",
    "رغم التعب والسهر، ستبقى الفرحة أكبر.",
    "جبال النجاح لا يمكن تسلقها بأيدي في الجيوب.",
    "لا وقت للكسل، كل دقيقة لها ثمن."
]

# الجدول الصباحي ورسائله
MORNING_SCHEDULE = [
    ("03:00", "daily_plan", "🚀 <b>خطة يومك الدراسي!</b>\n\n- 14 ساعة تركيز\n- 5 صلوات على وقتهم\n\nابدأ يومك بنية صافية وتوكل على الله.\nكل ساعة بتقربك من حلمك!", 2),
    ("04:25", "prayer_1", "🕋 <b>صلاة الفجر يا بطل!</b>\n\n\"الصلاة خير من النوم\"\nقوم اتوضى وصلّي، وابدأ يومك بطاقة ربانية.", 2),
    ("08:00", "breakfast", "☕ <b>فطار وراحة خفيفة</b>\n\nافتح الشباك، خد نفس عميق، واشرب حاجة سخنة.\nخد بريك علشان ترجع أقوى.", 1),
    ("08:30", "back_to_study", "📝 <b>يلا نرجع ننجز!</b>\n\nورقك قدامك، تركيزك في السقف!\nالنجاح مستني اللي يسعى له.", 3),
    ("11:00", "short_break", "⏸ <b>استراحة سريعة ؛ّم دقيقة</b>\n\nقوم اتحرك شوية، افصل دماغك من المذاكرة.\nبس بلاش تغرق في الموبايل!", 1),
    ("11:15", "back_after_break", "⚡ <b>رجعنا نذاكر تاني!</b>\n\nالراحة خلصت، والإنجاز بينادي.\nركز وشوف هتوصل لفين النهارده.", 3),
    ("12:51", "prayer_2", "🕛 <b>صلاة الظهر</b>\n\nقوم صلّي وارجع بكمل يومك براحة قلب.\nربنا معااك.", 2),
    ("13:01", "after_prayer_study", "📚 <b>مذاكرة بعد الصلاة</b>\n\nالطاقة رجعت.. والمهمة لسه ما خلصتش.\nشد حيلك.", 3),
    ("14:00", "nap_time", "💤 <b>وقت القيلولة / الراحة</b>\n\nريح جسمك ودماغك شوية.\nالراحة جزء من الإنجاز.", 1),
    ("15:30", "wake_up", "⏰ <b>يلا فوق!</b>\n\nاستعد نكمل باقي اليوم بقوة.\nلسه في وقت تنجز فيه كتير.", 1),
    ("16:28", "prayer_3", "🕋 <b>صلاة العصر</b>\n\nافصل شوية عن الدنيا، وصلي.\nكل ما تتقرب من ربنا، ربنا يقربك من حلمك.", 2),
    ("16:38", "study_3", "📖 <b>نكمل مذاكرة تاني!</b>\n\nخد نفس.. ركّز.. وكل حاجة هتبقى تمام.", 3),
    ("19:39", "prayer_4", "🌇 <b>صلاة المغرب</b>\n\nقوم صلّي، وادعي إن تعبك مايروحش هدر.\nالصلوات بتنور لك الطريق.", 2),
    ("21:06", "prayer_5", "🌙 <b>صلاة العشاء</b>\n\nالختام بيكون دايمًا مع ربنا.\nصلِّي بخشوع، واطلب منه الثبات.", 2),
    ("21:30", "evaluation", "📈 <b>تقييم يومك الدراسي</b>\n\n- ساعات المذاكرة: 13.5\n- الصلوات: 5/5\n- الاستراحات: تمام\n\nإنت بطل بجد!\nكل تعبك ده هتلاقيه في النتيجة.", 2)
]

# الجدول المسائي ورسائله
EVENING_SCHEDULE = [
    ("16:00", "evening_plan", "🌆 <b>الهدف الليلي الدراسي!</b>\n\n- تبدأ من الآن حتى 4:00 فجراً\n- هدفك: 12 ساعة مذاكرة\n- الصلوات: الفجر ✅ / العشاء ✅\n\nابدأ خطتك بقلب قوي وهمة عالية، وخلّي نيتك لله.", 2),
    ("16:35", "evening_study", "📖 <b>وقت الإنجاز الحقيقي!</b>\n\nابدأ مذاكرتك، وكل ساعة بتعدي هي استثمار في مستقبلك.", 3),
    ("20:00", "dinner_break", "☕ <b>استراحة سريعة</b>\n\nاتعشا، وارجع أكمل.\nالتركيز محتاج طاقة.", 1),
    ("20:30", "night_study", "📝 <b>عودة للمذاكرة!</b>\n\nخد نفس عميق وابدأ صفحة جديدة من الإنجاز.", 3),
    ("21:10", "prayer_5", "🕋 <b>صلاة العشاء</b>\n\nربنا بيختم يومك بنور. قوم صلي بخشوع، وادعي ربنا يثبتك.", 2),
    ("01:00", "long_break", "💤 <b>استراحة طويلة نصف ساعة</b>\n\nريح جسمك، افصل دماغك شوية.\nممكن تتمشى أو تسمع حاجة خفيفة، بس خليك قريب من هدفك.", 1),
    ("04:25", "prayer_1", "🕋 <b>صلاة الفجر</b>\n\nلو لسه صاحي، قوم صلّي.\nالفجر هو بداية يوم جديد، حتى لو لسه بتختم.", 2),
    ("04:05", "night_evaluation", "📈 <b>تقييم يومك الليلي</b>\n\n- عدد ساعات المذاكرة: 12\n- الصلوات: العشاء ✅ / الفجر ✅\n\n<b>حققت هدفك الليلي؟</b>", 2)
]

# إرسال رسالة مهمة مع مهلة زمنية للمشاركة
def send_group_task_message(group_id, task_type, text, points=1, deadline_minutes=10):
    """إرسال رسالة مهمة للمجموعة مع زر للمشاركة ومهلة زمنية"""
    try:
        # الحصول على المجموعة من قاعدة البيانات
        group = Group.query.get(group_id)
        if not group:
            logger.error(f"لم يتم العثور على المجموعة {group_id}")
            return None
            
        # الحصول على تتبع جدول المجموعة ليوم اليوم
        schedule_type = 'morning' if group.morning_schedule_enabled else 'evening' if group.evening_schedule_enabled else 'custom'
        schedule = GroupScheduleTracker.get_or_create_for_today(group_id, schedule_type)
        
        # إضافة زر للمشاركة في المهمة
        deadline_text = f"⏰ يمكنك الانضمام خلال {deadline_minutes} دقائق فقط"
        
        # إضافة معلومات النقاط
        points_text = f"🏆 ستحصل على {points} نقاط عند المشاركة"
        
        # إنشاء نص الرسالة الكامل
        full_text = f"{text}\n\n{deadline_text}\n{points_text}"
        
        # إنشاء زر المشاركة
        keyboard = {
            "inline_keyboard": [
                [{
                    "text": "✅ انضم للمهمة",
                    "callback_data": f"task_join:{task_type}:{schedule.id}"
                }]
            ]
        }
        
        # إرسال الرسالة
        message = send_group_message(group.telegram_id, full_text, keyboard)
        if not message:
            logger.error(f"فشل إرسال رسالة المهمة للمجموعة {group.telegram_id}")
            return None
            
        # إنشاء سجل المهمة في قاعدة البيانات
        task = GroupTaskTracker.create_task(
            schedule_id=schedule.id,
            task_type=task_type,
            message_id=message.get('message_id'),
            deadline_minutes=deadline_minutes,
            points=points
        )
        
        logger.info(f"تم إرسال رسالة المهمة {task_type} للمجموعة {group.telegram_id}")
        return task
    except Exception as e:
        logger.error(f"خطأ في إرسال رسالة المهمة للمجموعة {group_id}: {e}")
        return None


# معالجة الانضمام لمهمة
def handle_task_join(task_type, schedule_id, user_id, chat_id, callback_query_id):
    """معالجة طلب الانضمام لمهمة"""
    try:
        # الحصول على المهمة من قاعدة البيانات
        schedule_id = int(schedule_id)
        task = GroupTaskTracker.query.filter_by(schedule_id=schedule_id, task_type=task_type).first()
        
        if not task:
            answer_callback_query(callback_query_id, "❌ لم يتم العثور على المهمة المطلوبة")
            return False
            
        # التحقق من مهلة المهمة
        if not task.is_open():
            answer_callback_query(callback_query_id, "❌ انتهت مهلة الانضمام لهذه المهمة خليك جاهز المهمه الجيه")
            return False
            
        # الحصول على بيانات المستخدم
        user = User.get_or_create(user_id)
        
        # الحصول على بيانات الجدول
        schedule = task.schedule
        group = Group.query.get(schedule.group_id)
        
        # إنشاء مشارك للمجموعة إذا لم يكن موجوداً
        group_participant = GroupParticipant.get_or_create(group.id, user.id)
        
        # إضافة المستخدم كمشارك في المهمة
        participant = task.add_participant(user.id)
        
        if not participant:
            answer_callback_query(callback_query_id, "❌ لم يتم تسجيل مشاركتك في المهمة")
            return False
            
        # إرسال تأكيد للمستخدم
        answer_callback_query(
            callback_query_id, 
            f"✅ تم تسجيل مشاركتك في مهمة {get_task_name(task_type)}! (+{participant.points_earned} نقطة)"
        )
        
        logger.info(f"تم تسجيل المستخدم {user_id} في المهمة {task_type} للمجموعة {chat_id}")
        return True
    except Exception as e:
        logger.error(f"خطأ في معالجة الانضمام للمهمة: {e}")
        answer_callback_query(callback_query_id, "❌ حدث خطأ أثناء معالجة طلبك")
        return False


# الحصول على اسم المهمة
def get_task_name(task_type):
    """الحصول على الاسم العربي للمهمة"""
    task_names = {
        # المهام الأساسية
        'prayer_1': 'صلاة الفجر',
        'study_1': 'المذاكرة الأولى',
        'prayer_2': 'صلاة الظهر',
        'study_2': 'المذاكرة الثانية',
        'prayer_3': 'صلاة العصر',
        'study_3': 'المراجعة',
        'prayer_4': 'صلاة المغرب',
        'prayer_5': 'صلاة العشاء',
        'meal_1': 'الإفطار',
        'meal_2': 'العشاء',
        
        # مهام الجدول الصباحي
        'daily_plan': 'خطة اليوم الدراسي',
        'morning_join': 'المعسكر الصباحي',
        'breakfast': 'فطور وراحة',
        'back_to_study': 'العودة للمذاكرة',
        'short_break': 'استراحة قصيرة',
        'back_after_break': 'العودة بعد الراحة',
        'after_prayer_study': 'مذاكرة بعد الصلاة',
        'nap_time': 'وقت القيلولة',
        'wake_up': 'الاستيقاظ',
        'evaluation': 'تقييم اليوم',
        
        # مهام الجدول المسائي
        'evening_join': 'المعسكر الليلي',
        'evening_plan': 'الهدف الليلي الدراسي',
        'evening_study': 'وقت الإنجاز الحقيقي',
        'dinner_break': 'استراحة العشاء',
        'night_study': 'المذاكرة الليلية',
        'long_break': 'استراحة طويلة',
        'night_evaluation': 'تقييم اليوم الليلي',
        
        # مهام أخرى
        'early_sleep': 'النوم المبكر',
        'tahajjud': 'قيام الليل',
        'custom': 'مهمة مخصصة'
    }
    return task_names.get(task_type, task_type)


# وظائف مهام الجدول

def send_task_by_type(group_id, task_type, schedule_type='morning'):
    """إرسال مهمة بناءً على نوعها ونوع الجدول"""
    # اختيار الجدول المناسب
    schedule = MORNING_SCHEDULE if schedule_type == 'morning' else EVENING_SCHEDULE
    
    # البحث عن المهمة في الجدول
    for _, task_id, message, points in schedule:
        if task_id == task_type:
            # إضافة اقتباس تحفيزي عشوائي
            motivation = random.choice(MOTIVATIONAL_QUOTES)
            text = f"{message}\n\n✨ {motivation}"
            
            # إرسال المهمة
            return send_group_task_message(group_id, task_type, text, points=points, deadline_minutes=10)
    
    # إذا لم يتم العثور على المهمة، استخدم النص الافتراضي
    task_name = get_task_name(task_type)
    text = f"<b>{task_name}</b>\n\nحان موعد {task_name}.\nانضم للمهمة لتحصل على النقاط."
    return send_group_task_message(group_id, task_type, text, points=2, deadline_minutes=10)


# مهام الجدول الصباحي

# إرسال مهمة خطة اليوم الدراسي
def send_daily_plan_task(group_id):
    """إرسال مهمة خطة اليوم الدراسي"""
    return send_task_by_type(group_id, 'daily_plan')


# إرسال رسالة صلاة الفجر للمجموعة
def send_fajr_prayer_task(group_id):
    """إرسال مهمة صلاة الفجر للمجموعة"""
    return send_task_by_type(group_id, 'prayer_1')


# إرسال مهمة الفطور والراحة
def send_breakfast_task(group_id):
    """إرسال مهمة الفطور والراحة"""
    return send_task_by_type(group_id, 'breakfast')


# إرسال مهمة العودة للمذاكرة
def send_back_to_study_task(group_id):
    """إرسال مهمة العودة للمذاكرة"""
    return send_task_by_type(group_id, 'back_to_study')


# إرسال مهمة استراحة قصيرة
def send_short_break_task(group_id):
    """إرسال مهمة استراحة قصيرة"""
    return send_task_by_type(group_id, 'short_break')


# إرسال مهمة العودة بعد الراحة
def send_back_after_break_task(group_id):
    """إرسال مهمة العودة بعد الراحة"""
    return send_task_by_type(group_id, 'back_after_break')


# إرسال مهمة صلاة الظهر
def send_dhuhr_prayer_task(group_id):
    """إرسال مهمة صلاة الظهر"""
    return send_task_by_type(group_id, 'prayer_2')


# إرسال مهمة المذاكرة بعد الصلاة
def send_after_prayer_study_task(group_id):
    """إرسال مهمة المذاكرة بعد الصلاة"""
    return send_task_by_type(group_id, 'after_prayer_study')


# إرسال مهمة وقت القيلولة
def send_nap_time_task(group_id):
    """إرسال مهمة وقت القيلولة"""
    return send_task_by_type(group_id, 'nap_time')


# إرسال مهمة الاستيقاظ
def send_wake_up_task(group_id):
    """إرسال مهمة الاستيقاظ"""
    return send_task_by_type(group_id, 'wake_up')


# إرسال مهمة صلاة العصر
def send_asr_prayer_task(group_id):
    """إرسال مهمة صلاة العصر"""
    return send_task_by_type(group_id, 'prayer_3')


# إرسال مهمة المراجعة
def send_review_study_task(group_id):
    """إرسال مهمة المراجعة"""
    return send_task_by_type(group_id, 'study_3')


# إرسال مهمة صلاة المغرب
def send_maghrib_prayer_task(group_id):
    """إرسال مهمة صلاة المغرب"""
    return send_task_by_type(group_id, 'prayer_4')


# إرسال مهمة صلاة العشاء
def send_isha_prayer_task(group_id):
    """إرسال مهمة صلاة العشاء"""
    return send_task_by_type(group_id, 'prayer_5')


# إرسال مهمة تقييم اليوم
def send_evaluation_task(group_id):
    """إرسال مهمة تقييم اليوم"""
    return send_task_by_type(group_id, 'evaluation')


# مهام الجدول المسائي

# إرسال مهمة خطة اليوم الليلي
def send_evening_plan_task(group_id):
    """إرسال مهمة خطة اليوم الليلي"""
    return send_task_by_type(group_id, 'evening_plan', schedule_type='evening')


# إرسال مهمة المذاكرة المسائية
def send_evening_study_task(group_id):
    """إرسال مهمة المذاكرة المسائية"""
    return send_task_by_type(group_id, 'evening_study', schedule_type='evening')


# إرسال مهمة استراحة العشاء
def send_dinner_break_task(group_id):
    """إرسال مهمة استراحة العشاء"""
    return send_task_by_type(group_id, 'dinner_break', schedule_type='evening')


# إرسال مهمة المذاكرة الليلية
def send_night_study_task(group_id):
    """إرسال مهمة المذاكرة الليلية"""
    return send_task_by_type(group_id, 'night_study', schedule_type='evening')


# إرسال مهمة الاستراحة الطويلة
def send_long_break_task(group_id):
    """إرسال مهمة الاستراحة الطويلة"""
    return send_task_by_type(group_id, 'long_break', schedule_type='evening')


# إرسال مهمة تقييم اليوم الليلي
def send_night_evaluation_task(group_id):
    """إرسال مهمة تقييم اليوم الليلي"""
    return send_task_by_type(group_id, 'night_evaluation', schedule_type='evening')


# إرسال مهمة مخصصة للمجموعة
def send_custom_task(group_id, task_title, task_description, task_type, points=1, deadline_minutes=10):
    """إرسال مهمة مخصصة للمجموعة"""
    try:
        # التحقق من المجموعة
        group = Group.query.get(group_id)
        if not group:
            logger.error(f"لم يتم العثور على المجموعة {group_id}")
            return None
            
        # التحقق من تفعيل الجدول المخصص
        if not group.custom_schedule_enabled:
            logger.error(f"الجدول المخصص غير مفعل للمجموعة {group_id}")
            return None
        
        # إضافة اقتباس تحفيزي عشوائي
        motivation = random.choice(MOTIVATIONAL_QUOTES)
        
        # نص المهمة
        text = f"""
✏️ <b>{task_title}</b>

{task_description}

✨ {motivation}
"""
        
        # إرسال المهمة
        return send_group_task_message(group_id, task_type, text, points, deadline_minutes)
    except Exception as e:
        logger.error(f"خطأ في إرسال المهمة المخصصة: {e}")
        return None


# معالجة أمر إنشاء مهمة مخصصة
def handle_custom_task_command(group_id, admin_id, command_text):
    """معالجة أمر إنشاء مهمة مخصصة"""
    try:
        # التحقق من المجموعة
        group = Group.query.get(group_id)
        if not group:
            return "❌ لم يتم العثور على المجموعة"
            
        # التحقق من صلاحيات المشرف
        if admin_id != group.admin_id:
            return "❌ هذا الأمر متاح فقط لمشرف المجموعة"
            
        # التحقق من تفعيل الجدول المخصص
        if not group.custom_schedule_enabled:
            return "❌ الجدول المخصص غير مفعل لهذه المجموعة. قم بتفعيله أولاً من إعدادات الجدول"
        
        # تحليل نص الأمر
        params = command_text.strip().split('|')
        if len(params) < 3:
            return "❌ صيغة غير صحيحة. الرجاء استخدام:\n/custom_task <عنوان المهمة> | <وصف المهمة> | <نوع المهمة> | <النقاط> | <المهلة بالدقائق>"
        
        # الحصول على المعلومات
        task_title = params[0].strip()
        task_description = params[1].strip()
        task_type = params[2].strip() if len(params) > 2 else 'custom'
        
        # النقاط والمهلة
        try:
            points = int(params[3].strip()) if len(params) > 3 else 1
            deadline_minutes = int(params[4].strip()) if len(params) > 4 else 10
        except ValueError:
            return "❌ يجب أن تكون النقاط والمهلة أرقاماً صحيحة"
        
        # إرسال المهمة
        task = send_custom_task(group_id, task_title, task_description, task_type, points, deadline_minutes)
        if task:
            return f"✅ تم إنشاء المهمة \"{task_title}\" بنجاح! (النقاط: {points}, المهلة: {deadline_minutes} دقيقة)"
        else:
            return "❌ حدث خطأ في إنشاء المهمة"
    except Exception as e:
        logger.error(f"خطأ في معالجة أمر المهمة المخصصة: {e}")
        return "❌ حدث خطأ في معالجة الأمر"


# للتوافق مع الأكواد السابقة - إرسال رسالة المذاكرة الأولى للمجموعة
def send_first_study_task(group_id, schedule_type='morning'):
    """إرسال مهمة المذاكرة الأولى للمجموعة"""
    if schedule_type == 'morning':
        return send_back_to_study_task(group_id)
    else:  # evening
        return send_evening_study_task(group_id)
