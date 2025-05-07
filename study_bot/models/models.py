"""
نماذج قاعدة البيانات
يحتوي على تعريفات جداول قاعدة البيانات ووظائف إدارة البيانات
"""

from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, Boolean, DateTime, BigInteger, ForeignKey, Text, Float
from sqlalchemy.orm import relationship

from study_bot.models import db


# نموذج المستخدم
class User(db.Model):
    """نموذج لتخزين معلومات المستخدمين"""
    
    __tablename__ = 'user'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String(64), nullable=True)
    first_name = Column(String(64), nullable=True)
    last_name = Column(String(64), nullable=True)
    registration_date = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    preferred_schedule = Column(String(20), default='none')  # 'morning', 'evening', 'custom', 'none'
    motivation_enabled = Column(Boolean, default=False)
    
    # نقاط المستخدم
    morning_points = Column(Integer, default=0)
    evening_points = Column(Integer, default=0)
    total_points = Column(Integer, default=0)
    
    # إعدادات محسن الإشعارات الذكي
    smart_notifications_enabled = Column(Boolean, default=True)  # تفعيل/إيقاف المحسن الذكي
    notification_time_sensitivity = Column(Integer, default=2)  # مستوى الحساسية (1=منخفض، 2=متوسط، 3=عالي)
    max_daily_notifications = Column(Integer, default=10)  # الحد الأقصى للإشعارات اليومية
    
    # العلاقات
    schedules = relationship('UserSchedule', backref='user', lazy=True)
    activities = relationship('UserActivity', backref='user', lazy=True)
    participations = relationship('ScheduleTracker', backref='user', lazy=True)
    group_participations = relationship('GroupParticipant', backref='user', lazy=True)
    camp_participations = relationship('CampParticipant', backref='user', lazy=True)
    
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
        return user
    
    def update_points(self, points, schedule_type):
        """تحديث نقاط المستخدم"""
        if schedule_type == 'morning':
            self.morning_points += points
        elif schedule_type == 'evening':
            self.evening_points += points
        
        self.total_points += points
        db.session.commit()
    
    def update_smart_notifications_settings(self, enabled=None, sensitivity=None, max_daily=None):
        """تحديث إعدادات الإشعارات الذكية"""
        if enabled is not None:
            self.smart_notifications_enabled = enabled
        
        if sensitivity is not None:
            self.notification_time_sensitivity = sensitivity
        
        if max_daily is not None:
            self.max_daily_notifications = max_daily
        
        db.session.commit()
    
    def get_full_name(self):
        """الحصول على الاسم الكامل للمستخدم"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.username:
            return f"@{self.username}"
        else:
            return f"مستخدم {self.telegram_id}"


# نموذج المجموعة
class Group(db.Model):
    """نموذج لتخزين معلومات المجموعات"""
    
    __tablename__ = 'group'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    title = Column(String(255), nullable=False)
    creation_date = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    admin_id = Column(BigInteger, nullable=True)  # معرف المستخدم المدير
    motivation_enabled = Column(Boolean, default=True)
    schedule_type = Column(String(20), default='none')  # 'morning', 'evening', 'custom', 'none'
    custom_schedule_text = Column(Text, nullable=True)
    
    # العلاقات
    participants = relationship('GroupParticipant', backref='group', lazy=True)
    camps = relationship('CustomCamp', backref='group', lazy=True)
    
    def __repr__(self):
        return f"<Group {self.telegram_id}: {self.title}>"
    
    @classmethod
    def get_or_create(cls, telegram_id, **kwargs):
        """الحصول على مجموعة موجودة أو إنشاء مجموعة جديدة"""
        group = cls.query.filter_by(telegram_id=telegram_id).first()
        if not group:
            group = cls(telegram_id=telegram_id, **kwargs)
            db.session.add(group)
            db.session.commit()
        return group
    
    def deactivate(self):
        """إلغاء تفعيل المجموعة"""
        self.is_active = False
        db.session.commit()


# نموذج مشارك المجموعة
class GroupParticipant(db.Model):
    """نموذج لتخزين مشاركي المجموعات"""
    
    __tablename__ = 'group_participant'
    
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey('group.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    join_date = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    total_points = Column(Integer, default=0)
    morning_points = Column(Integer, default=0)
    evening_points = Column(Integer, default=0)
    custom_points = Column(Integer, default=0)
    
    def __repr__(self):
        return f"<GroupParticipant user={self.user_id} in group {self.group_id}>"


# نموذج متتبع جدول المجموعة
class GroupScheduleTracker(db.Model):
    """نموذج لتتبع مشاركات المستخدمين في جداول المجموعات"""
    
    __tablename__ = 'group_schedule_tracker'
    
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey('group.id'), nullable=False)
    date = Column(DateTime, default=datetime.utcnow)
    schedule_type = Column(String(20), nullable=False)  # 'morning', 'evening', 'custom'
    
    # حالة المهام
    morning_message_sent = Column(Boolean, default=False)
    evening_message_sent = Column(Boolean, default=False)
    
    # مهام الجدول الصباحي
    daily_plan_sent = Column(Boolean, default=False)
    prayer_1_sent = Column(Boolean, default=False)
    breakfast_sent = Column(Boolean, default=False)
    study_1_sent = Column(Boolean, default=False)
    prayer_2_sent = Column(Boolean, default=False)
    study_2_sent = Column(Boolean, default=False)
    break_sent = Column(Boolean, default=False)
    return_after_break_sent = Column(Boolean, default=False)
    prayer_3_sent = Column(Boolean, default=False)
    study_3_sent = Column(Boolean, default=False)
    prayer_4_sent = Column(Boolean, default=False)
    prayer_5_sent = Column(Boolean, default=False)
    evaluation_sent = Column(Boolean, default=False)
    
    # مهام الجدول المسائي
    join_sent = Column(Boolean, default=False)
    study_eve_1_sent = Column(Boolean, default=False)
    prayer_eve_1_sent = Column(Boolean, default=False)
    study_eve_2_sent = Column(Boolean, default=False)
    prayer_eve_2_sent = Column(Boolean, default=False)
    study_eve_3_sent = Column(Boolean, default=False)
    evaluation_eve_sent = Column(Boolean, default=False)
    early_sleep_sent = Column(Boolean, default=False)
    
    def __repr__(self):
        return f"<GroupScheduleTracker for group {self.group_id} on {self.date.strftime('%Y-%m-%d')}>"


# نموذج مهمة المجموعة
class GroupTaskTracker(db.Model):
    """نموذج لتتبع مهام المجموعات"""
    
    __tablename__ = 'group_task_tracker'
    
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey('group.id'), nullable=False)
    date = Column(DateTime, default=datetime.utcnow)
    task_name = Column(String(50), nullable=False)
    task_type = Column(String(20), nullable=False)  # 'prayer', 'study', 'meal', etc.
    scheduled_time = Column(DateTime, nullable=False)
    message_id = Column(Integer, nullable=True)
    is_sent = Column(Boolean, default=False)
    points = Column(Integer, default=1)
    deadline_minutes = Column(Integer, default=10)
    
    # العلاقات
    participants = relationship('GroupTaskParticipant', backref='task', lazy=True)
    
    def __repr__(self):
        return f"<GroupTaskTracker {self.task_name} for group {self.group_id}>"


# نموذج مشارك في مهمة المجموعة
class GroupTaskParticipant(db.Model):
    """نموذج لتخزين مشاركات المستخدمين في مهام المجموعات"""
    
    __tablename__ = 'group_task_participant'
    
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey('group_task_tracker.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    participation_time = Column(DateTime, default=datetime.utcnow)
    points_earned = Column(Integer, default=0)
    
    def __repr__(self):
        return f"<GroupTaskParticipant user={self.user_id} in task {self.task_id}>"


# نموذج تفضيلات الإشعارات
class NotificationPreference(db.Model):
    """نموذج لتخزين تفضيلات الإشعارات للمستخدمين"""
    
    __tablename__ = 'notification_preference'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    morning_reminder = Column(Boolean, default=True)
    evening_reminder = Column(Boolean, default=True)
    prayer_reminder = Column(Boolean, default=True)
    study_reminder = Column(Boolean, default=True)
    meal_reminder = Column(Boolean, default=True)
    evaluation_reminder = Column(Boolean, default=True)
    motivational_messages = Column(Boolean, default=True)
    preferred_reminder_time = Column(Integer, default=5)  # عدد الدقائق قبل الموعد
    
    def __repr__(self):
        return f"<NotificationPreference for user {self.user_id}>"


# نموذج متتبع الجدول
class ScheduleTracker(db.Model):
    """نموذج لتتبع إنجازات المستخدمين في الجداول اليومية"""
    
    __tablename__ = 'schedule_tracker'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    date = Column(DateTime, default=datetime.utcnow)
    schedule_type = Column(String(20), nullable=False)  # 'morning', 'evening', 'custom'
    
    # مهام الجدول الصباحي
    joined = Column(Boolean, default=False)
    prayer_1 = Column(Boolean, default=False)
    meal_1 = Column(Boolean, default=False)
    study_1 = Column(Boolean, default=False)
    prayer_2 = Column(Boolean, default=False)
    study_2 = Column(Boolean, default=False)
    return_after_break = Column(Boolean, default=False)
    prayer_3 = Column(Boolean, default=False)
    study_3 = Column(Boolean, default=False)
    prayer_4 = Column(Boolean, default=False)
    prayer_5 = Column(Boolean, default=False)
    evaluation = Column(Boolean, default=False)
    
    # مهام الجدول المسائي
    # (تم استخدام نفس الأعمدة المشتركة مع الجدول الصباحي)
    early_sleep = Column(Boolean, default=False)
    
    # النقاط
    total_points = Column(Integer, default=0)
    
    def __repr__(self):
        return f"<ScheduleTracker for user {self.user_id} on {self.date.strftime('%Y-%m-%d')}>"
    
    @classmethod
    def get_or_create(cls, user_id, date, schedule_type):
        """الحصول على متتبع موجود أو إنشاء متتبع جديد"""
        # البحث عن تاريخ اليوم فقط (بدون الوقت)
        start_of_day = datetime(date.year, date.month, date.day, 0, 0, 0)
        end_of_day = datetime(date.year, date.month, date.day, 23, 59, 59)
        
        tracker = cls.query.filter(
            cls.user_id == user_id,
            cls.schedule_type == schedule_type,
            cls.date >= start_of_day,
            cls.date <= end_of_day
        ).first()
        
        if not tracker:
            tracker = cls(
                user_id=user_id,
                date=date,
                schedule_type=schedule_type
            )
            db.session.add(tracker)
            db.session.commit()
        
        return tracker


# نموذج جدول المستخدم
class UserSchedule(db.Model):
    """نموذج لتخزين جداول المستخدمين المخصصة"""
    
    __tablename__ = 'user_schedule'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    schedule_data = Column(Text, nullable=False)  # JSON data for schedule
    is_active = Column(Boolean, default=True)
    creation_date = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<UserSchedule {self.name} for user {self.user_id}>"


# نموذج نشاط المستخدم
class UserActivity(db.Model):
    """نموذج لتخزين أنشطة المستخدمين"""
    
    __tablename__ = 'user_activity'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    activity_type = Column(String(50), nullable=False)  # 'prayer', 'study', 'join', etc.
    schedule_type = Column(String(20), nullable=True)  # 'morning', 'evening', 'custom'
    timestamp = Column(DateTime, default=datetime.utcnow)
    points = Column(Integer, default=0)
    details = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<UserActivity {self.activity_type} by user {self.user_id}>"


# نموذج الرسالة التحفيزية
class MotivationalMessage(db.Model):
    """نموذج لتخزين الرسائل التحفيزية"""
    
    __tablename__ = 'motivational_message'
    
    id = Column(Integer, primary_key=True)
    content = Column(Text, nullable=False)
    category = Column(String(50), default='general')  # 'study', 'prayer', 'morning', 'evening', 'general'
    author = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    
    def __repr__(self):
        return f"<MotivationalMessage {self.id}: {self.content[:30]}...>"


# نموذج إحصائيات النظام
class SystemStat(db.Model):
    """نموذج لتخزين إحصائيات النظام"""
    
    __tablename__ = 'system_stat'
    
    id = Column(Integer, primary_key=True)
    stat_name = Column(String(50), nullable=False, unique=True)
    stat_value = Column(Integer, default=0)
    last_reset = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<SystemStat {self.stat_name}: {self.stat_value}>"
    
    @classmethod
    def increment(cls, stat_name, amount=1):
        """زيادة قيمة إحصائية معينة"""
        stat = cls.query.filter_by(stat_name=stat_name).first()
        if not stat:
            stat = cls(stat_name=stat_name, stat_value=amount)
            db.session.add(stat)
        else:
            stat.stat_value += amount
        db.session.commit()
        return stat.stat_value
    
    @classmethod
    def get_value(cls, stat_name):
        """الحصول على قيمة إحصائية معينة"""
        stat = cls.query.filter_by(stat_name=stat_name).first()
        return stat.stat_value if stat else 0