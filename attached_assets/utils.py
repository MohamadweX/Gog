#!/usr/bin/env python3
"""
وحدة المساعدة
تحتوي على وظائف مساعدة للبوت وواجهة الويب
"""

import os
import sys
from datetime import datetime, timedelta
import json
import random

def get_morning_schedule_text(tracker):
    """الحصول على نص الجدول الصباحي"""
    # التحقق من اكتمال المهام وإضافة رموز لعرضها
    joined_status = "✅" if tracker.joined else "⬜️"
    prayer_1_status = "✅" if tracker.prayer_1 else "⬜️"
    meal_1_status = "✅" if tracker.meal_1 else "⬜️"
    study_1_status = "✅" if tracker.study_1 else "⬜️"
    prayer_2_status = "✅" if tracker.prayer_2 else "⬜️"
    study_2_status = "✅" if tracker.study_2 else "⬜️"
    return_status = "✅" if tracker.return_after_break else "⬜️"
    prayer_3_status = "✅" if tracker.prayer_3 else "⬜️"
    study_3_status = "✅" if tracker.study_3 else "⬜️"
    prayer_4_status = "✅" if tracker.prayer_4 else "⬜️"
    prayer_5_status = "✅" if tracker.prayer_5 else "⬜️"
    evaluation_status = "✅" if tracker.evaluation else "⬜️"
    
    # بناء نص الجدول
    schedule_text = f"""
<b>🌞 الجدول الصباحي - {tracker.date.strftime('%Y-%m-%d')}</b>

<b>الصباح:</b>
{joined_status} تسجيل الحضور
{prayer_1_status} صلاة الفجر (5:00 ص)
{meal_1_status} الإفطار (7:00 ص)
{study_1_status} بدء المذاكرة (8:00 ص)

<b>الظهر:</b>
{prayer_2_status} صلاة الظهر (12:00 م)
{study_2_status} المذاكرة بعد الظهر (1:00 م)
{return_status} العودة بعد الراحة (2:30 م)

<b>العصر والمساء:</b>
{prayer_3_status} صلاة العصر (3:30 م)
{study_3_status} المراجعة (4:00 م)
{prayer_4_status} صلاة المغرب (6:30 م)
{prayer_5_status} صلاة العشاء (8:00 م)

<b>نهاية اليوم:</b>
{evaluation_status} تقييم اليوم (10:00 م)

<b>حالة الجدول:</b> {get_completion_status(tracker)}
"""
    
    return schedule_text

def get_evening_schedule_text(tracker):
    """الحصول على نص الجدول المسائي"""
    # التحقق من اكتمال المهام وإضافة رموز لعرضها
    joined_status = "✅" if tracker.joined else "⬜️"
    study_1_status = "✅" if tracker.study_1 else "⬜️"
    prayer_1_status = "✅" if tracker.prayer_1 else "⬜️"
    study_2_status = "✅" if tracker.study_2 else "⬜️"
    prayer_2_status = "✅" if tracker.prayer_2 else "⬜️"
    study_3_status = "✅" if tracker.study_3 else "⬜️"
    evaluation_status = "✅" if tracker.evaluation else "⬜️"
    early_sleep_status = "✅" if tracker.early_sleep else "⬜️"
    
    # بناء نص الجدول
    schedule_text = f"""
<b>🌙 الجدول المسائي - {tracker.date.strftime('%Y-%m-%d')}</b>

<b>ما بعد الظهر:</b>
{joined_status} تسجيل الحضور
{study_1_status} بدء المراجعة (3:00 م)

<b>المساء:</b>
{prayer_1_status} صلاة المغرب (6:30 م)
{study_2_status} بدء واجب/تدريب (7:00 م)
{prayer_2_status} صلاة العشاء (8:00 م)
{study_3_status} الحفظ/القراءة الخفيفة (8:30 م)

<b>نهاية اليوم:</b>
{evaluation_status} تقييم اليوم (10:00 م)
{early_sleep_status} النوم المبكر (11:00 م)

<b>حالة الجدول:</b> {get_completion_status(tracker)}
"""
    
    return schedule_text

def get_custom_schedule_text(tracker, custom_schedule):
    """الحصول على نص الجدول المخصص"""
    # بناء نص الجدول المخصص
    schedule_text = f"""
<b>✏️ الجدول المخصص - {tracker.date.strftime('%Y-%m-%d')}</b>

"""
    
    # إضافة المهام المخصصة
    for task_key, task_info in custom_schedule.items():
        task_name = task_info.get('name', task_key)
        task_time = task_info.get('time', '')
        
        # التحقق من حالة المهمة
        task_status = "✅" if getattr(tracker, task_key, False) else "⬜️"
        
        # بناء سطر المهمة
        task_line = f"{task_status} {task_name}"
        if task_time:
            task_line += f" ({task_time})"
        
        schedule_text += task_line + "\n"
    
    # إضافة حالة الجدول
    schedule_text += f"\n<b>حالة الجدول:</b> {get_completion_status(tracker)}"
    
    return schedule_text

def get_completion_status(tracker):
    """الحصول على حالة إكمال الجدول"""
    if tracker.completed:
        return "✅ مكتمل"
    
    # حساب نسبة الإكمال
    completed_count = 0
    total_count = 0
    
    if tracker.schedule_type == 'morning':
        tasks = [
            'joined', 'prayer_1', 'meal_1', 'study_1', 
            'prayer_2', 'study_2', 'return_after_break',
            'prayer_3', 'study_3', 'prayer_4', 'prayer_5', 
            'evaluation'
        ]
    elif tracker.schedule_type == 'evening':
        tasks = [
            'joined', 'study_1', 'prayer_1', 'study_2',
            'prayer_2', 'study_3', 'evaluation', 'early_sleep'
        ]
    else:
        # للجداول المخصصة، نعتبر المهام الأساسية
        tasks = [
            'joined', 'study_1', 'evaluation'
        ]
    
    # حساب عدد المهام المكتملة
    for task_name in tasks:
        total_count += 1
        if getattr(tracker, task_name, False):
            completed_count += 1
    
    # حساب النسبة المئوية للإكمال
    completion_percentage = int((completed_count / total_count) * 100) if total_count > 0 else 0
    
    # بناء شريط التقدم
    progress_bar = generate_progress_bar(completed_count, total_count, 10)
    
    return f"{progress_bar} {completion_percentage}%"

def generate_progress_bar(current, total, length=10):
    """إنشاء شريط تقدم نصي"""
    progress = min(1, current / total) if total > 0 else 0
    filled_length = int(length * progress)
    
    bar = '█' * filled_length + '░' * (length - filled_length)
    
    return bar

def get_motivational_messages(category='general'):
    """الحصول على قائمة بالرسائل التحفيزية"""
    # قائمة الرسائل التحفيزية حسب الفئة
    messages = {
        'general': [
            "لا تؤجل عمل اليوم إلى الغد. ابدأ الآن! 💪",
            "العلم نور والجهل ظلام، واصل التعلم لتنير حياتك ✨",
            "الإصرار والمثابرة هما مفتاح النجاح. استمر! 🔑",
            "كل خطوة صغيرة تقربك من أهدافك الكبيرة 🎯",
            "المذاكرة المنتظمة أفضل من المذاكرة المكثفة قبل الاختبار 📚",
            "لا تقارن تقدمك بتقدم الآخرين، ركز على تحسين نفسك 🌱",
            "المعرفة كنز لا يفنى، والتعلم استثمار دائم ⚡",
            "العقل السليم في الجسم السليم. تذكر أن تأخذ استراحة وتمارس الرياضة 🏃‍♂️",
            "لا تخف من الفشل، فهو أول خطوات النجاح 🧗‍♀️",
            "تذكر دائمًا أن الصعوبات هي التي تصنع العظماء 🌟"
        ],
        'morning': [
            "صباح الخير! يوم جديد وفرصة جديدة للتعلم والإنجاز ☀️",
            "بداية قوية تعني يومًا ناجحًا. ابدأ صباحك بالمذاكرة 📝",
            "صباح النشاط! استغل طاقتك الصباحية في أصعب المهام 🌄",
            "ما تفعله في الصباح يحدد مسار يومك. اجعله مليئًا بالإنتاجية 🌅",
            "الصباح الباكر هو أفضل وقت للتركيز والإبداع. استثمره جيدًا ⏰",
            "مع كل شروق شمس، فرصة جديدة للتفوق ☀️",
            "الطالب الناجح يبدأ يومه مبكرًا ومستعدًا للتحديات 🏆",
            "بدايات الصباح هي أنقى أوقات التفكير. استغلها في المذاكرة 📚"
        ],
        'evening': [
            "المساء وقت مثالي للمراجعة وتثبيت المعلومات 🌙",
            "كثير من العلماء يفضلون المذاكرة في المساء. استفد من هذا الوقت الهادئ 🌠",
            "قبل النوم، راجع ما تعلمته اليوم لتثبيت المعلومات في ذاكرتك 🧠",
            "المساء فرصة للتخطيط لليوم القادم واستكمال ما تبقى من مهام 📋",
            "استغل هدوء الليل في القراءة والحفظ 📖",
            "لا تنسَ أخذ قسط كافٍ من النوم، فهو أساس للنجاح في اليوم التالي 💤",
            "في المساء، اترك القلق جانبًا واستمتع بإنجازاتك اليومية 🌛",
            "المثابرة في المساء تؤتي ثمارها في الصباح ✨"
        ],
        'study': [
            "ركز على الفهم وليس الحفظ. المعرفة الحقيقية تأتي من الفهم العميق 🧩",
            "التكرار هو مفتاح الحفظ. كرر المعلومات المهمة لتثبيتها 🔁",
            "قسّم وقتك بين المواد المختلفة للحفاظ على تركيزك وفعاليتك 🕒",
            "استخدم تقنية بومودورو: 25 دقيقة دراسة، 5 دقائق راحة ⏱️",
            "اشرح ما تعلمته لشخص آخر، فهذا أفضل اختبار لفهمك 🗣️",
            "الملخصات والخرائط الذهنية تساعد في تنظيم المعلومات وتذكرها 📊",
            "ابحث عن تطبيقات عملية للمعلومات التي تتعلمها، فهذا يعزز فهمك 💡",
            "تعلم من أخطائك وأسئلتك الخاطئة، فهي فرص ذهبية للتحسن 🔍",
            "لا تتردد في طلب المساعدة عندما تحتاجها. التعلم رحلة جماعية 🤝",
            "اقرأ بصوت مرتفع عند المذاكرة، فهذا يساعد في التركيز والتذكر 🔊"
        ]
    }
    
    # استخدام الفئة المطلوبة أو الفئة العامة كبديل
    category_messages = messages.get(category, messages['general'])
    
    return category_messages

def get_random_motivational_message(category='general'):
    """الحصول على رسالة تحفيزية عشوائية"""
    messages = get_motivational_messages(category)
    return random.choice(messages)
