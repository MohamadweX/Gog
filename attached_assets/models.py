#!/usr/bin/env python3
"""
نماذج قاعدة البيانات
يحتوي على تعريفات جداول قاعدة البيانات ووظائف إدارة البيانات
"""

from datetime import datetime, timedelta
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
import sys
import os

# استيراد الإعدادات
from study_bot.config import DATABASE_URL, logger

# تعريف القاعدة الأساسية للنماذج
class Base(DeclarativeBase):
    pass

# إنشاء كائن قاعدة البيانات
db = SQLAlchemy(model_class=Base)

# هذه الدالة تستخدم لإعداد قاعدة البيانات مع تطبيق فلاسك
def setup_db(app):
    """إعداد قاعدة البيانات مع تطبيق فلاسك"""
    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    db.init_app(app)
    
    # إنشاء الجداول إذا لم تكن موجودة
    with app.app_context():
        db.create_all()
        logger.info("تم إعداد قاعدة البيانات بنجاح")


# نموذج المستخدم
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    telegram_id = db.Column(db.BigInteger, unique=True, nullable=False)
    username = db.Column(db.String(64), nullable=True)
    first_name = db.Column(db.String(64), nullable=True)
    last_name = db.Column(db.String(64), nullable=True)
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    preferred_schedule = db.Column(db.String(20), default='none')  # 'morning', 'evening', 'custom', 'none'
    motivation_enabled = db.Column(db.Boolean, default=False)
    
    # نقاط المستخدم
    morning_points = db.Column(db.Integer, default=0)
    evening_points = db.Column(db.Integer, default=0)
    total_points = db.Column(db.Integer, default=0)
    
    # إعدادات محسن الإشعارات الذكي
    smart_notifications_enabled = db.Column(db.Boolean, default=True)  # تفعيل/إيقاف المحسن الذكي
    notification_time_sensitivity = db.Column(db.Integer, default=2)  # مستوى الحساسية (1=منخفض، 2=متوسط، 3=عالي)
    max_daily_notifications = db.Column(db.Integer, default=10)  # الحد الأقصى للإشعارات اليومية
    
    # العلاقات
    schedules = db.relationship('UserSchedule', backref='user', lazy=True)
    activities = db.relationship('UserActivity', backref='user', lazy=True)
    participations = db.relationship('ScheduleTracker', backref='user', lazy=True)
    
    def __repr__(self):
        return f"<User {self.telegram_id}>"
    
    @classmethod
    def get_or_create(cls, telegram_id, **kwargs):
        """الحصول على مستخدم موجود أو إنشاء مستخدم جديد"""
        user = cls.query.filter_by(telegram_id=telegram_id).first()
        if not user:
            user = cls(telegram_id=telegram_id, **kwargs)
            db.session.add(user)
            db.session.commit()
            logger.info(f"تم إنشاء مستخدم جديد: {telegram_id}")
        return user
    
    def update_points(self, points, schedule_type):
        """تحديث نقاط المستخدم"""
        if schedule_type == 'morning':
            self.morning_points += points
        elif schedule_type == 'evening':
            self.evening_points += points
        
        self.total_points += points
        db.session.commit()
        logger.info(f"تم تحديث نقاط المستخدم {self.telegram_id}: +{points} ({schedule_type})")
    
    def update_smart_notifications_settings(self, enabled=None, sensitivity=None, max_daily=None):
        """تحديث إعدادات الإشعارات الذكية"""
        if enabled is not None:
            self.smart_notifications_enabled = enabled
        
        if sensitivity is not None:
            self.notification_time_sensitivity = max(min(sensitivity, 3), 1)  # القيمة بين 1 و 3
        
        if max_daily is not None:
            self.max_daily_notifications = max(max_daily, 1)  # على الأقل إشعار واحد
        
        db.session.commit()
        logger.info(f"تم تحديث إعدادات الإشعارات الذكية للمستخدم {self.telegram_id}")
        return True
    
    def get_optimal_notification_times(self):
        """الحصول على أوقات الإشعارات المثلى للمستخدم"""
        if not self.smart_notifications_enabled:
            return {}
        
        # الحصول على تفضيلات الإشعارات
        notification_prefs = NotificationPreference.query.filter_by(user_id=self.id).all()
        
        # تجميع الأوقات المثلى
        optimal_times = {}
        for pref in notification_prefs:
            key = f"{pref.schedule_type}_{pref.task_type}"
            optimal_times[key] = pref.optimal_time
        
        return optimal_times


# نموذج المجموعة
class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    telegram_id = db.Column(db.BigInteger, unique=True, nullable=False)
    title = db.Column(db.String(255), nullable=True)
    join_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # إعدادات المجموعة
    admin_id = db.Column(db.BigInteger, nullable=True)
    morning_schedule_enabled = db.Column(db.Boolean, default=False)
    evening_schedule_enabled = db.Column(db.Boolean, default=False)
    custom_schedule_enabled = db.Column(db.Boolean, default=False)
    motivation_enabled = db.Column(db.Boolean, default=False)
    setup_complete = db.Column(db.Boolean, default=False)
    setup_in_progress = db.Column(db.Boolean, default=False)
    setup_stage = db.Column(db.String(50), default='not_started')  # لتتبع مرحلة الإعداد
    
    # العلاقات
    schedules = db.relationship('GroupSchedule', backref='group', lazy=True)
    participations = db.relationship('GroupParticipant', backref='group', lazy=True)
    
    def __repr__(self):
        return f"<Group {self.telegram_id}>"
    
    @classmethod
    def get_or_create(cls, telegram_id, **kwargs):
        """الحصول على مجموعة موجودة أو إنشاء مجموعة جديدة"""
        group = cls.query.filter_by(telegram_id=telegram_id).first()
        if not group:
            group = cls(telegram_id=telegram_id, **kwargs)
            db.session.add(group)
            db.session.commit()
            logger.info(f"تم إنشاء مجموعة جديدة: {telegram_id}")
        return group
    
    def update_schedule_status(self, schedule_type, enabled):
        """تحديث حالة تفعيل الجدول"""
        if schedule_type == 'morning':
            self.morning_schedule_enabled = enabled
        elif schedule_type == 'evening':
            self.evening_schedule_enabled = enabled
        elif schedule_type == 'custom':
            self.custom_schedule_enabled = enabled
        
        db.session.commit()
        logger.info(f"تم تحديث حالة الجدول {schedule_type} للمجموعة {self.telegram_id}: {enabled}")
        
    def get_active_participants(self, schedule_type=None):
        """الحصول على المشاركين النشطين في المجموعة"""
        query = GroupParticipant.query.filter_by(group_id=self.id, is_active=True)
        
        if schedule_type:
            # تصفية حسب نوع الجدول إذا تم تحديده
            if schedule_type == 'morning':
                query = query.filter_by(joined_morning=True)
            elif schedule_type == 'evening':
                query = query.filter_by(joined_evening=True)
                
        return query.all()
    
    def get_top_participants(self, schedule_type=None, limit=10):
        """الحصول على أفضل المشاركين من حيث النقاط"""
        query = GroupParticipant.query.filter_by(group_id=self.id, is_active=True)
        
        if schedule_type == 'morning':
            query = query.order_by(GroupParticipant.morning_points.desc())
        elif schedule_type == 'evening':
            query = query.order_by(GroupParticipant.evening_points.desc())
        else:
            query = query.order_by(GroupParticipant.total_points.desc())
            
        return query.limit(limit).all()


# نموذج جدول المستخدم
class UserSchedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    schedule_type = db.Column(db.String(20), nullable=False)  # 'morning', 'evening', 'custom'
    creation_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # جدول مخصص
    is_custom = db.Column(db.Boolean, default=False)
    custom_schedule = db.Column(db.JSON, nullable=True)  # جدول بتنسيق JSON
    
    def __repr__(self):
        return f"<UserSchedule {self.user_id} - {self.schedule_type}>"
    
    @classmethod
    def create_or_update(cls, user_id, schedule_type, is_custom=False, custom_schedule=None):
        """إنشاء أو تحديث جدول المستخدم"""
        schedule = cls.query.filter_by(user_id=user_id, schedule_type=schedule_type).first()
        if not schedule:
            schedule = cls(
                user_id=user_id,
                schedule_type=schedule_type,
                is_custom=is_custom,
                custom_schedule=custom_schedule
            )
            db.session.add(schedule)
        else:
            schedule.is_custom = is_custom
            schedule.custom_schedule = custom_schedule
        
        db.session.commit()
        logger.info(f"تم تحديث جدول المستخدم {user_id}: {schedule_type}")
        return schedule


# نموذج جدول المجموعة
class GroupSchedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    schedule_type = db.Column(db.String(20), nullable=False)  # 'morning', 'evening', 'custom'
    creation_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # جدول مخصص
    is_custom = db.Column(db.Boolean, default=False)
    custom_schedule = db.Column(db.JSON, nullable=True)  # جدول بتنسيق JSON
    
    def __repr__(self):
        return f"<GroupSchedule {self.group_id} - {self.schedule_type}>"


# نموذج نشاط المستخدم
class UserActivity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    activity_type = db.Column(db.String(50), nullable=False)  # e.g., 'join_morning', 'prayer', 'study_session'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    points_earned = db.Column(db.Integer, default=0)
    schedule_type = db.Column(db.String(20), nullable=False)  # 'morning' or 'evening'
    
    def __repr__(self):
        return f"<UserActivity {self.user_id} - {self.activity_type}>"
    
    @classmethod
    def record_activity(cls, user_id, activity_type, schedule_type, points=0):
        """تسجيل نشاط جديد للمستخدم"""
        activity = cls(
            user_id=user_id,
            activity_type=activity_type,
            schedule_type=schedule_type,
            points_earned=points
        )
        db.session.add(activity)
        
        # تحديث نقاط المستخدم
        user = User.query.get(user_id)
        if user:
            user.update_points(points, schedule_type)
        
        db.session.commit()
        logger.info(f"تم تسجيل نشاط جديد للمستخدم {user_id}: {activity_type} (+{points})")
        return activity


# نموذج مشارك المجموعة
class GroupParticipant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    join_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # حالة المشاركة في الجداول
    joined_morning = db.Column(db.Boolean, default=False)  # مشارك في الجدول الصباحي
    joined_evening = db.Column(db.Boolean, default=False)  # مشارك في الجدول المسائي
    morning_day_streak = db.Column(db.Integer, default=0)  # عدد أيام المشاركة المتتالية في الجدول الصباحي
    evening_day_streak = db.Column(db.Integer, default=0)  # عدد أيام المشاركة المتتالية في الجدول المسائي
    
    # نقاط في المجموعة
    morning_points = db.Column(db.Integer, default=0)  # نقاط الجدول الصباحي
    evening_points = db.Column(db.Integer, default=0)  # نقاط الجدول المسائي
    total_points = db.Column(db.Integer, default=0)  # مجموع النقاط
    daily_points = db.Column(db.Integer, default=0)  # نقاط اليوم
    
    # علاقة مع المستخدم
    user = db.relationship('User', backref=db.backref('groups', lazy=True))
    
    def __repr__(self):
        return f"<GroupParticipant {self.group_id} - {self.user_id}>"
    
    @classmethod
    def get_or_create(cls, group_id, user_id):
        """الحصول على مشارك موجود أو إنشاء مشارك جديد"""
        participant = cls.query.filter_by(group_id=group_id, user_id=user_id).first()
        if not participant:
            participant = cls(group_id=group_id, user_id=user_id)
            db.session.add(participant)
            db.session.commit()
            logger.info(f"تم إنشاء مشارك جديد: مجموعة {group_id}, مستخدم {user_id}")
        return participant
    
    def update_points(self, points, schedule_type):
        """تحديث نقاط المشارك"""
        self.daily_points += points
        self.total_points += points
        
        if schedule_type == 'morning':
            self.morning_points += points
        elif schedule_type == 'evening':
            self.evening_points += points
        
        db.session.commit()
        logger.info(f"تم تحديث نقاط المشارك {self.user_id} في المجموعة {self.group_id}: +{points} ({schedule_type})")
    
    def update_participation(self, schedule_type, participating=True):
        """تحديث حالة مشاركة المستخدم في جدول معين"""
        if schedule_type == 'morning':
            self.joined_morning = participating
            if participating:
                self.morning_day_streak += 1
        elif schedule_type == 'evening':
            self.joined_evening = participating
            if participating:
                self.evening_day_streak += 1
        
        db.session.commit()
        logger.info(f"تم تحديث حالة مشاركة المستخدم {self.user_id} في المجموعة {self.group_id} للجدول {schedule_type}: {participating}")
    
    def reset_daily_points(self):
        """إعادة تعيين نقاط اليوم"""
        self.daily_points = 0
        db.session.commit()
        logger.info(f"تم إعادة تعيين نقاط اليوم للمشارك {self.user_id} في المجموعة {self.group_id}")



# نموذج متابعة الجدول
class ScheduleTracker(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow().date)
    schedule_type = db.Column(db.String(20), nullable=False)  # 'morning', 'evening', 'custom'
    
    # تتبع الأنشطة
    # مهام مشتركة
    joined = db.Column(db.Boolean, default=False)  # الانضمام للمعسكر
    prayer_1 = db.Column(db.Boolean, default=False)  # صلاة الفجر أو المغرب
    study_1 = db.Column(db.Boolean, default=False)  # المذاكرة الأولى
    prayer_2 = db.Column(db.Boolean, default=False)  # صلاة الظهر أو العشاء
    study_2 = db.Column(db.Boolean, default=False)  # المذاكرة الثانية
    prayer_3 = db.Column(db.Boolean, default=False)  # صلاة العصر
    study_3 = db.Column(db.Boolean, default=False)  # المراجعة أو الحفظ
    prayer_4 = db.Column(db.Boolean, default=False)  # صلاة المغرب
    prayer_5 = db.Column(db.Boolean, default=False)  # صلاة العشاء
    evaluation = db.Column(db.Boolean, default=False)  # تقييم اليوم
    completed = db.Column(db.Boolean, default=False)  # إكمال الجدول

    # مهام الجدول الصباحي
    meal_1 = db.Column(db.Boolean, default=False)  # الإفطار
    return_after_break = db.Column(db.Boolean, default=False)  # العودة بعد الراحة
    
    # مهام الجدول المسائي
    meal = db.Column(db.Boolean, default=False)  # العشاء
    early_sleep = db.Column(db.Boolean, default=False)  # النوم المبكر
    tahajjud = db.Column(db.Boolean, default=False)  # قيام الليل
    
    # مهام أخرى
    daily_plan = db.Column(db.Boolean, default=False)  # خطة اليوم
    break_time = db.Column(db.Boolean, default=False)  # استراحة
    nap = db.Column(db.Boolean, default=False)  # قيلولة
    wake_up = db.Column(db.Boolean, default=False)  # الاستيقاظ من القيلولة
    
    def __repr__(self):
        return f"<ScheduleTracker {self.user_id} - {self.schedule_type} - {self.date}>"
    
    @classmethod
    def get_or_create_for_today(cls, user_id, schedule_type):
        """الحصول على متابعة الجدول ليوم اليوم أو إنشاء سجل جديد"""
        today = datetime.utcnow().date()
        tracker = cls.query.filter_by(
            user_id=user_id, 
            schedule_type=schedule_type,
            date=today
        ).first()
        
        if not tracker:
            tracker = cls(
                user_id=user_id,
                schedule_type=schedule_type,
                date=today
            )
            db.session.add(tracker)
            db.session.commit()
            logger.info(f"تم إنشاء متابعة جدول جديدة للمستخدم {user_id}: {schedule_type}")
        
        return tracker
    
    def mark_task_complete(self, task_name, record_activity=True):
        """تحديد مهمة كمكتملة وإضافة النقاط المناسبة"""
        from study_bot.config import MORNING_POINTS, EVENING_POINTS
        
        # تحديد جدول النقاط المناسب
        points_table = MORNING_POINTS if self.schedule_type == 'morning' else EVENING_POINTS
        
        # تحديث حالة المهمة
        if hasattr(self, task_name) and not getattr(self, task_name):
            setattr(self, task_name, True)
            
            # تسجيل النشاط وإضافة النقاط إذا كانت المهمة موجودة في جدول النقاط
            if task_name in points_table and record_activity:
                points = points_table[task_name]
                UserActivity.record_activity(
                    user_id=self.user_id,
                    activity_type=f"{task_name}_{self.schedule_type}",
                    schedule_type=self.schedule_type,
                    points=points
                )
            
            # التحقق من اكتمال الجدول
            self.check_completion()
            
            db.session.commit()
            logger.info(f"تم تحديد المهمة {task_name} كمكتملة للمستخدم {self.user_id}")
            return True
        
        return False
    
    def check_completion(self):
        """التحقق من اكتمال الجدول بالكامل"""
        # تحديد المهام المطلوبة حسب نوع الجدول
        required_tasks = []
        
        if self.schedule_type == 'morning':
            required_tasks = [
                'joined', 'prayer_1', 'meal_1', 'study_1', 
                'prayer_2', 'study_2', 'return_after_break',
                'prayer_3', 'study_3', 'prayer_4', 'prayer_5', 
                'evaluation'
            ]
        elif self.schedule_type == 'evening':
            required_tasks = [
                'joined', 'study_1', 'prayer_1', 'study_2',
                'prayer_2', 'study_3', 'evaluation', 'early_sleep'
            ]
        
        # التحقق من اكتمال جميع المهام المطلوبة
        all_completed = all(getattr(self, task) for task in required_tasks)
        
        # تحديث حالة الاكتمال وإضافة نقاط الاكتمال
        if all_completed and not self.completed:
            self.completed = True
            
            # إضافة نقاط لإكمال الجدول
            from study_bot.config import MORNING_POINTS, EVENING_POINTS
            points_table = MORNING_POINTS if self.schedule_type == 'morning' else EVENING_POINTS
            
            UserActivity.record_activity(
                user_id=self.user_id,
                activity_type=f"complete_day_{self.schedule_type}",
                schedule_type=self.schedule_type,
                points=points_table.get("complete_day", 5)
            )
            
            logger.info(f"تم إكمال الجدول {self.schedule_type} بالكامل للمستخدم {self.user_id}")


# نموذج تتبع جدول المجموعة
class GroupScheduleTracker(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow().date)
    schedule_type = db.Column(db.String(20), nullable=False)  # 'morning', 'evening', 'custom'
    message_id = db.Column(db.Integer, nullable=True)  # معرف رسالة الجدول في المجموعة
    
    # حالة التفعيل
    is_active = db.Column(db.Boolean, default=True)
    join_message_id = db.Column(db.Integer, nullable=True)  # معرف رسالة الانضمام
    join_deadline = db.Column(db.DateTime, nullable=True)
    
    # الحقول المضافة
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    start_date = db.Column(db.DateTime, nullable=True)
    end_date = db.Column(db.DateTime, nullable=True)
    settings = db.Column(db.JSON, nullable=True)  # إعدادات إضافية للجدول
    participants_count = db.Column(db.Integer, default=0)  # عدد المشاركين اليوم
    completed_count = db.Column(db.Integer, default=0)  # عدد المكملين للجدول
    
    # علاقة مع المجموعة
    group = db.relationship('Group', backref=db.backref('schedule_trackers', lazy=True))
    
    def __repr__(self):
        return f"<GroupScheduleTracker {self.group_id} - {self.schedule_type} - {self.date}>"
    
    @classmethod
    def get_or_create_for_today(cls, group_id, schedule_type):
        """الحصول على متابعة جدول المجموعة ليوم اليوم أو إنشاء سجل جديد"""
        today = datetime.utcnow().date()
        tracker = cls.query.filter_by(
            group_id=group_id, 
            schedule_type=schedule_type,
            date=today
        ).first()
        
        if not tracker:
            tracker = cls(
                group_id=group_id,
                schedule_type=schedule_type,
                date=today
            )
            db.session.add(tracker)
            db.session.commit()
            logger.info(f"تم إنشاء متابعة جدول جديدة للمجموعة {group_id}: {schedule_type}")
        
        return tracker
    
    def set_join_message(self, message_id, deadline_minutes=15):
        """تعيين رسالة الانضمام وموعد انتهاء الانضمام"""
        self.join_message_id = message_id
        self.join_deadline = datetime.utcnow() + timedelta(minutes=deadline_minutes)
        db.session.commit()
        logger.info(f"تم تعيين رسالة الانضمام للمجموعة {self.group_id}: {message_id}")
    
    def update_participants_count(self, count=None):
        """تحديث عدد المشاركين"""
        if count is not None:
            self.participants_count = count
        else:
            # حساب عدد المشاركين من قاعدة البيانات
            if self.schedule_type == 'morning':
                self.participants_count = GroupParticipant.query.filter_by(group_id=self.group_id, joined_morning=True).count()
            elif self.schedule_type == 'evening':
                self.participants_count = GroupParticipant.query.filter_by(group_id=self.group_id, joined_evening=True).count()
        
        db.session.commit()
        logger.info(f"تم تحديث عدد المشاركين في المجموعة {self.group_id}: {self.participants_count}")
    
    def is_join_open(self):
        """التحقق من إمكانية الانضمام للجدول"""
        if not self.join_deadline:
            return False
        return datetime.utcnow() < self.join_deadline


# نموذج تفضيلات الإشعارات
class NotificationPreference(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    schedule_type = db.Column(db.String(20), nullable=False)  # 'morning', 'evening'
    task_type = db.Column(db.String(50), nullable=False)  # 'prayer', 'study', etc.
    optimal_time = db.Column(db.Time, nullable=True)  # الوقت المفضل للإشعار
    enabled = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f"<NotificationPreference {self.user_id} - {self.task_type}>"
    
    @classmethod
    def set_preference(cls, user_id, schedule_type, task_type, optimal_time=None, enabled=True):
        """تعيين تفضيل الإشعارات للمستخدم"""
        pref = cls.query.filter_by(
            user_id=user_id,
            schedule_type=schedule_type,
            task_type=task_type
        ).first()
        
        if not pref:
            pref = cls(
                user_id=user_id,
                schedule_type=schedule_type,
                task_type=task_type
            )
            db.session.add(pref)
        
        pref.optimal_time = optimal_time
        pref.enabled = enabled
        
        db.session.commit()
        logger.info(f"تم تعيين تفضيل الإشعارات للمستخدم {user_id}: {task_type} في {schedule_type}")
        return pref


# نموذج الرسائل التحفيزية
class MotivationalMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)  # 'general', 'study', 'morning', 'evening'
    
    def __repr__(self):
        return f"<MotivationalMessage {self.id} - {self.category}>"
    
    @classmethod
    def get_random_message(cls, category='general'):
        """الحصول على رسالة تحفيزية عشوائية"""
        import random
        messages = cls.query.filter_by(category=category).all()
        if not messages:
            # إذا لم تكن هناك رسائل في القاعدة، استخدم الرسائل الافتراضية
            default_messages = [ "🏁 ابدأ يومك بنية النجاح، وصدقني النهاية هتكون عظيمة.", "📚 كل صفحة بتفتحها، هي لبنة في مستقبل مشرق ليك.", "🔋 شحن طاقتك بيبدأ من إنك تؤمن بنفسك.", "🎯 هدفك يستاهل تعبك، خليك ثابت!", "🚀 كل ساعة مذاكرة = خطوة أقرب لحلمك الكبير.", "🛡️ المذاكرة هي سلاحك قدام أي تحدي.", "🌅 صباح الإنجاز بيبدأ من أول قرار تاخده تذاكر.", "📈 النجاح بيحب الناس اللي بتستمر، مش الناس اللي بس تبدأ.", "⚙️ التكرار بيخليك محترف… متزهقش!", "🏆 التعب مؤقت… بس النتيجة بتعيش معاك طول العمر.", "🔑 المذاكرة مش واجب… دي مفتاح حريتك.", "🔥 كل مرة تقول (مش قادر)، رد عليها بـ (لازم أوصل).", "💡 كل فكرة بتفهمها دلوقتي، هتسهّل عليك بكرة.", "🎓 اسعى تكون من القمة… عشان القاع زحمة.", "📅 النهارده هو أنسب وقت تبدأ فيه… مش بكرة!", "🔒 خليك مؤمن إن حلمك أمانة… والتعب حقه.", "⚡ الإنجاز مش بيجي صدفة… بيجي من تعبك.", "📖 الكتاب قدامك… ومستقبلك جواه.", "🧭 خليك دايمًا ماشي على طريق الهدف، حتى لو ببطء.", "📵 سيب السوشيال… وخد لحظة لنفسك تذاكر فيها.", "🌠 كل يوم بتذاكر فيه هو خطوة ناحية مستقبلك اللي بتحلم بيه.", "🎢 المذاكرة ساعات بتكون صعبة، بس النجاح أحلى من أي تعب.", "🧱 كل معلومة بتفهمها دلوقتي، هي حجر في بنيان مستقبلك.", "🌈 متستناش الحافز… ابني لنفسك عادة.", "🎮 اللعبة الحقيقية هي تكسب نفسك وتحقق حلمك.", "💼 اللي بياخد الموضوع بجد، هو اللي بيشيل الشهادة بفخر.", "🧠 لما تذاكر، إنت بتستثمر في أغلى حاجة عندك: عقلك.", "💥 متخليش الكسل يسرق منك المستقبل.", "⚓ لما تتعب، افتكر هدفك… وكمّل عشان توصله.", "🌻 الزرعة اللي بتسقيها كل يوم، هتطرح نجاح بعدين.", "📘 خليك دايمًا الشخص اللي حلمه أكبر من ظروفه.", "💎 الإنجاز مش في عدد الساعات… الإنجاز في تركيزك.", "🕹️ سيب اللعبة… وادخل لعبة النجاح الحقيقي.", "🧗 كل تحدي قدامك، هو فرصة تتخطاه وتكبر.", "🎯 المذاكرة دلوقتي = راحة نفسية وقت النتيجة.", "🌠 مينفعش توصل للنجوم وإنت مش عايز تطلع السلم.", "🔧 المذاكرة هي الورشة اللي بتصنع فيها مستقبلك.", "🎤 في يوم من الأيام، الناس هتسقف لك… بس ابدأ النهارده.", "📊 ذاكر وكأنك هتشرح لغيرك… دي أسرع طريقة للفهم.", "🧲 كل فكرة جديدة بتذاكرها، بتقربك من حلمك خطوة.", "🚧 التعب الحقيقي إنك متحاولش… مش إنك تفشل.", "🎖️ مش لازم تكون عبقري، بس لازم تكون مجتهد.", "⛳ هدفك مش بعيد… هو بس محتاج خطوة كمان.", "📓 خليك الشخص اللي دايمًا يختار يذاكر بدل ما يندم.", "💭 فكر في اللحظة اللي هتمسك فيها نتيجتك وتعيط من الفرح.", "🛎️ الوقت بيجري… بس قرارك هو اللي يحدد تضيعه ولا تستغله.", "🧃 خد استراحة لما تحتاج، بس متنساش ترجع تكمل.", "🎲 كل اختيار بتاخده النهارده بيحدد مستقبلك بكرة.", "⚖️ النجاح مش صدفة… هو نتيجة قرارات يومية بسيطة.", "🚴 التعب دلوقتي = راحة وثقة بعدين.", "💥 لحظة تركيز دلوقتي، أحسن من ساعات ندم بعدين.", "🎁 المذاكرة هدية بتقدمها لنفسك، ماتأخرهاش.", "🔭 شوف حلمك بوضوح، وخليه هو المحفز ليك كل يوم.", "🧨 كسر الكسل أول الطريق… وبعدها كل حاجة هتمشي.", "🌌 أحلامك الكبيرة بتبدأ من أبسط قرار تاخده: تذاكر.", "📍 خليك في الحاضر… عشان المستقبل هيشكر تعبك ده.", "🎒 اليوم اللي تعدي فيه من غير مذاكرة… ضاع عليك كتير!", "🏅 كل إنجاز صغير هو نقطة بتتقرب بيها للهدف الكبير.", "🗂️ رتّب وقتك، وإنت هتتفاجئ بكمية الإنجاز اللي هتعمله.", "✨ خليك الشخص اللي حلمه بيخليه يصحى من النوم بحماس.", "📢 اسكت صوت الكسل… وافتح كتاب النجاح.", "🧱 كل معلومة بتفهمها دلوقتي، هتفتح لك باب بعدين.", "🕰️ الاستمرارية أهم من الكمال… ذاكر شوية كل يوم.", "📘 الحياة مش سهلة… بس بالتعليم بتكون أعدل.", "📶 ارفع من مستوى تركيزك، وهنشوف مستوى نجاحك بيعلى.", "🔐 اجتهد كأن باب الفرصة هيتقفل بكرة.", "📍 لو مش دلوقتي، إمتى؟!", "🏃 الجري وراء الحلم بيبدأ بخطوة اسمها مذاكرة.", "🪄 مفيش سحر… في التزام.", "📚 ورقة النهاردة، هي نتيجة بكرة.", "🎯 ذاكر كأنك بتحضر لمستقبل ابنك.", "🔭 كل ما تحلم أكبر، كل ما محتاج تتعب أكتر.", "🎸 متغنيش النجاح… عيشه بمذاكرتك.", "🛠️ المذاكرة هي ورشة بناء المستقبل… اشتغل على نفسك.", "⛅ التعب سحابة وهتعدي… بس نجاحك هيفضل منوّر.", "📍 لو النهاردة صعب، بكرة هيكون أسهل بسببك.", "🕹️ اللعب الحقيقي في الحياة مش في الموبايل… في الإنجاز.", "🎯 وقتك هو استثمارك… ذاكر كويس.", "📘 ذاكر علشان نفسك، مش علشان حد تاني.", "🌠 في يوم من الأيام، هتقول: الحمد لله إني ما استسلمتش." ]

            # اختار رساله عشوائيه من الرسائل الافتراضيه 
            
            return random.choice(default_messages)
        
        return random.choice(messages).message


# نموذج إحصائيات النظام
class SystemStat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, default=datetime.utcnow().date)
    active_users = db.Column(db.Integer, default=0)
    messages_sent = db.Column(db.Integer, default=0)
    activities_recorded = db.Column(db.Integer, default=0)
    points_awarded = db.Column(db.Integer, default=0)
    
    def __repr__(self):
        return f"<SystemStat {self.date}>"
        
    @classmethod
    def get_or_create_for_today(cls):
        """الحصول على إحصائيات اليوم أو إنشاء سجل جديد"""
        today = datetime.utcnow().date()
        stat = cls.query.filter_by(date=today).first()
        
        if not stat:
            stat = cls(date=today)
            db.session.add(stat)
            db.session.commit()
        
        return stat
    
    @classmethod
    def increment(cls, field_name, amount=1):
        """زيادة قيمة حقل إحصائي محدد"""
        stat = cls.get_or_create_for_today()
        
        if hasattr(stat, field_name):
            current_value = getattr(stat, field_name)
            setattr(stat, field_name, current_value + amount)
            db.session.commit()
            return True
        
        return False


# نموذج تتبع مهام المجموعة
class GroupTaskTracker(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    schedule_id = db.Column(db.Integer, db.ForeignKey('group_schedule_tracker.id'), nullable=False)
    task_type = db.Column(db.String(50), nullable=False)  # e.g., 'prayer_1', 'study_1'
    message_id = db.Column(db.Integer, nullable=True)  # معرف رسالة المهمة في المجموعة
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    deadline = db.Column(db.DateTime, nullable=True)  # وقت انتهاء المهمة
    is_completed = db.Column(db.Boolean, default=False)  # هل انتهت المهمة
    participant_count = db.Column(db.Integer, default=0)  # عدد المشاركين في المهمة
    points_per_participant = db.Column(db.Integer, default=1)  # النقاط لكل مشارك
    
    # علاقة مع جدول المجموعة
    schedule = db.relationship('GroupScheduleTracker', backref=db.backref('tasks', lazy=True))
    
    # علاقة مع المشاركين في المهمة
    participants = db.relationship('GroupTaskParticipant', backref='task', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<GroupTaskTracker {self.schedule_id} - {self.task_type}>"
    
    @classmethod
    def create_task(cls, schedule_id, task_type, message_id=None, deadline_minutes=10, points=1):
        """إنشاء مهمة جديدة للمجموعة"""
        task = cls(
            schedule_id=schedule_id,
            task_type=task_type,
            message_id=message_id,
            deadline=datetime.utcnow() + timedelta(minutes=deadline_minutes),
            points_per_participant=points
        )
        db.session.add(task)
        db.session.commit()
        logger.info(f"تم إنشاء مهمة جديدة للجدول {schedule_id}: {task_type}")
        return task
    
    def is_open(self):
        """التحقق من إمكانية المشاركة في المهمة"""
        if not self.deadline:
            return False
        return datetime.utcnow() < self.deadline and not self.is_completed
    
    def add_participant(self, user_id):
        """إضافة مشارك للمهمة"""
        # التحقق من أن المستخدم لم يشارك بالفعل
        existing = GroupTaskParticipant.query.filter_by(
            task_id=self.id,
            user_id=user_id
        ).first()
        
        if existing:
            return existing
            
        # التحقق من أن المهمة ما زالت مفتوحة
        if not self.is_open():
            return None
            
        # إنشاء سجل جديد للمشاركة
        participant = GroupTaskParticipant(
            task_id=self.id,
            user_id=user_id,
            points_earned=self.points_per_participant
        )
        db.session.add(participant)
        
        # تحديث عدد المشاركين
        self.participant_count += 1
        
        # إضافة النقاط للمستخدم في المجموعة
        schedule = GroupScheduleTracker.query.get(self.schedule_id)
        if schedule:
            group_participant = GroupParticipant.query.filter_by(
                group_id=schedule.group_id,
                user_id=user_id
            ).first()
            
            if group_participant:
                group_participant.daily_points += self.points_per_participant
                if schedule.schedule_type == 'morning':
                    group_participant.morning_points += self.points_per_participant
                elif schedule.schedule_type == 'evening':
                    group_participant.evening_points += self.points_per_participant
                group_participant.total_points += self.points_per_participant
        
        db.session.commit()
        logger.info(f"تمت إضافة المستخدم {user_id} إلى المهمة {self.task_type}")
        return participant
    
    def mark_as_completed(self):
        """تعليم المهمة كمكتملة"""
        self.is_completed = True
        db.session.commit()
        logger.info(f"تم تعليم المهمة {self.task_type} كمكتملة")


# نموذج مشاركي مهام المجموعة
class GroupTaskParticipant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('group_task_tracker.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    points_earned = db.Column(db.Integer, default=1)  # النقاط المكتسبة من هذه المهمة
    
    # علاقة مع المستخدم
    user = db.relationship('User', backref=db.backref('group_task_participations', lazy=True))
    
    def __repr__(self):
        return f"<GroupTaskParticipant {self.task_id} - {self.user_id}>"

    
    @classmethod
    def get_or_create_for_today(cls):
        """الحصول على إحصائيات اليوم أو إنشاء سجل جديد"""
        today = datetime.utcnow().date()
        stat = cls.query.filter_by(date=today).first()
        
        if not stat:
            stat = cls(date=today)
            db.session.add(stat)
            db.session.commit()
        
        return stat
    
    @classmethod
    def increment(cls, field_name, amount=1):
        """زيادة قيمة حقل إحصائي محدد"""
        stat = cls.get_or_create_for_today()
        
        if hasattr(stat, field_name):
            current_value = getattr(stat, field_name)
            setattr(stat, field_name, current_value + amount)
            db.session.commit()
            return True
        
        return False
