"""
نموذج المجموعة
يحتوي على تعريف نموذج المجموعة وخصائصها
"""

from datetime import datetime, timedelta
import pytz
import json
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text, ForeignKey, func
from sqlalchemy.orm import relationship

from study_bot.config import SCHEDULER_TIMEZONE
from study_bot.models import db

class Group(db.Model):
    """نموذج المجموعة"""
    __tablename__ = 'group'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    title = Column(String(255), nullable=True)
    username = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    is_private = Column(Boolean, default=False)
    is_authenticated = Column(Boolean, default=False)
    creation_date = Column(DateTime, default=datetime.now(SCHEDULER_TIMEZONE))
    admin_id = Column(Integer, nullable=True)
    admin_username = Column(String(100), nullable=True)
    
    # إعدادات المجموعة
    send_motivational = Column(Boolean, default=True)
    send_reports = Column(Boolean, default=True)
    allow_custom_tasks = Column(Boolean, default=True)
    timezone_offset = Column(Integer, default=3)  # بالساعات، الافتراضي هو توقيت السعودية (+3)
    language_code = Column(String(10), default='ar')
    
    # إعدادات جداول الدراسة
    morning_schedule_enabled = Column(Boolean, default=False)
    evening_schedule_enabled = Column(Boolean, default=False)
    custom_schedule_enabled = Column(Boolean, default=False)
    motivation_enabled = Column(Boolean, default=True)
    
    # إحصائيات المجموعة
    total_messages = Column(Integer, default=0)
    total_tasks = Column(Integer, default=0)
    total_participants = Column(Integer, default=0)
    total_completions = Column(Integer, default=0)
    
    # علاقات
    schedules = relationship('GroupScheduleTracker', backref='group', lazy=True)
    tasks = relationship('GroupTaskTracker', backref='group', lazy=True)
    participants = relationship('GroupTaskParticipant', backref='group', lazy=True)
    motivational_messages = relationship('MotivationalMessage', backref='group', lazy=True)
    camps = relationship('CustomCamp', backref='group', lazy=True)
    
    def get_timezone(self):
        """الحصول على المنطقة الزمنية للمجموعة"""
        try:
            return pytz.FixedOffset(self.timezone_offset * 60)
        except:
            return SCHEDULER_TIMEZONE
    
    def get_active_schedule(self, schedule_type='morning'):
        """الحصول على الجدول النشط للمجموعة"""
        return GroupScheduleTracker.query.filter_by(
            group_id=self.id,
            schedule_type=schedule_type,
            is_active=True
        ).first()
    
    def get_active_tasks(self, limit=10):
        """الحصول على المهام النشطة للمجموعة"""
        return GroupTaskTracker.query.filter_by(
            group_id=self.id,
            is_expired=False
        ).order_by(GroupTaskTracker.scheduled_time.desc()).limit(limit).all()
    
    def get_active_participants(self):
        """الحصول على المشاركين النشطين في المجموعة"""
        return GroupTaskParticipant.query.filter_by(
            group_id=self.id,
            is_active=True
        ).all()
    
    def get_active_camps(self):
        """الحصول على المعسكرات النشطة في المجموعة"""
        now = datetime.now(SCHEDULER_TIMEZONE)
        
        from study_bot.models import CustomCamp
        return CustomCamp.query.filter_by(
            group_id=self.id,
            is_active=True
        ).filter(
            CustomCamp.start_date <= now,
            CustomCamp.end_date >= now
        ).all()
    
    def get_completion_stats(self, days=7):
        """الحصول على إحصائيات إكمال المهام للمجموعة"""
        from study_bot.models import GroupTaskParticipant, User
        
        # تاريخ البداية
        start_date = datetime.now(SCHEDULER_TIMEZONE) - timedelta(days=days)
        
        # الحصول على المشاركين النشطين
        participants = db.session.query(
            GroupTaskParticipant, User
        ).join(
            User, GroupTaskParticipant.user_id == User.id
        ).filter(
            GroupTaskParticipant.group_id == self.id,
            GroupTaskParticipant.is_active == True,
            GroupTaskParticipant.last_completion_date >= start_date
        ).all()
        
        # إعداد البيانات
        stats = {
            'total_participants': len(participants),
            'total_completions': 0,
            'participants': []
        }
        
        for participant, user in participants:
            stats['total_completions'] += participant.total_completion_count
            
            part_info = {
                'user_id': user.id,
                'telegram_id': user.telegram_id,
                'name': user.get_full_name(),
                'completions': participant.total_completion_count,
                'streak': user.streak_days,
                'points': user.points,
                'last_completion': participant.last_completion_date.isoformat() if participant.last_completion_date else None
            }
            
            stats['participants'].append(part_info)
        
        # ترتيب المشاركين حسب عدد المهام المكتملة
        stats['participants'] = sorted(
            stats['participants'],
            key=lambda x: x['completions'],
            reverse=True
        )
        
        return stats
    
    def is_admin(self, user_id):
        """التحقق مما إذا كان المستخدم مشرفًا في المجموعة"""
        return self.admin_id == user_id
    
    def __repr__(self):
        return f'<Group {self.title or self.telegram_id}>'


class GroupScheduleTracker(db.Model):
    """نموذج متابعة جدول المجموعة"""
    __tablename__ = 'group_schedule_tracker'
    
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey('group.id'), nullable=False)
    schedule_type = Column(String(20), nullable=False, default='morning')  # morning, evening, custom
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now(SCHEDULER_TIMEZONE))
    updated_at = Column(DateTime, default=datetime.now(SCHEDULER_TIMEZONE), onupdate=datetime.now(SCHEDULER_TIMEZONE))
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    
    # إعدادات إضافية
    settings = Column(Text, nullable=True)  # JSON string of additional settings
    
    @classmethod
    def get_or_create_for_today(cls, group_id, schedule_type='morning'):
        """الحصول على أو إنشاء جدول للمجموعة ليوم اليوم"""
        now = datetime.now(SCHEDULER_TIMEZONE)
        today_start = datetime(now.year, now.month, now.day, 0, 0, 0, tzinfo=SCHEDULER_TIMEZONE)
        today_end = datetime(now.year, now.month, now.day, 23, 59, 59, tzinfo=SCHEDULER_TIMEZONE)
        
        # البحث عن جدول اليوم
        schedule = cls.query.filter_by(
            group_id=group_id,
            schedule_type=schedule_type,
            is_active=True
        ).filter(
            cls.created_at >= today_start,
            cls.created_at <= today_end
        ).first()
        
        # إنشاء جدول جديد إذا لم يتم العثور عليه
        if not schedule:
            schedule = cls(
                group_id=group_id,
                schedule_type=schedule_type,
                start_date=today_start,
                end_date=today_end
            )
            db.session.add(schedule)
            db.session.commit()
            
        return schedule
        
    def add_participant(self, user_id):
        """إضافة مشارك إلى الجدول"""
        # الحصول على أو إنشاء مشارك المجموعة
        participant = GroupTaskParticipant.get_or_create(self.group_id, user_id, self.schedule_type)
        
        return participant is not None
    
    def get_settings(self):
        """الحصول على إعدادات الجدول"""
        if not self.settings:
            return {}
        try:
            return json.loads(self.settings)
        except:
            return {}
    
    def set_settings(self, settings_dict):
        """تعيين إعدادات الجدول"""
        self.settings = json.dumps(settings_dict)
        db.session.commit()
    
    def update_setting(self, key, value):
        """تحديث إعداد محدد"""
        settings = self.get_settings()
        settings[key] = value
        self.set_settings(settings)
    
    def get_setting(self, key, default=None):
        """الحصول على إعداد محدد"""
        settings = self.get_settings()
        return settings.get(key, default)
    
    def __repr__(self):
        return f'<GroupScheduleTracker {self.group_id} - {self.schedule_type}>'


class GroupTaskTracker(db.Model):
    """نموذج متابعة مهام المجموعة"""
    __tablename__ = 'group_task_tracker'
    
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey('group.id'), nullable=False)
    task_type = Column(String(50), nullable=False)  # fajr_prayer, breakfast, daily_plan, etc.
    scheduled_time = Column(DateTime, default=datetime.now(SCHEDULER_TIMEZONE))
    deadline_minutes = Column(Integer, default=10)
    is_sent = Column(Boolean, default=False)
    sent_at = Column(DateTime, nullable=True)
    message = Column(Text, nullable=True)
    message_id = Column(Integer, nullable=True)
    join_button_text = Column(String(100), nullable=True)
    points = Column(Integer, default=1)  # النقاط المكتسبة عند إكمال المهمة
    schedule_id = Column(Integer, nullable=True)  # معرف جدول المجموعة المرتبط بالمهمة
    
    # علاقات
    participants = relationship('GroupTaskParticipant', secondary='group_task_participation', backref='completed_tasks', lazy=True)
    
    @classmethod
    def create_task(cls, schedule_id, task_type, message_id=None, deadline_minutes=10, points=1, message=None):
        """إنشاء مهمة جديدة"""
        # الحصول على معرف المجموعة من جدول المجموعة
        schedule = GroupScheduleTracker.query.get(schedule_id)
        if not schedule:
            return None
            
        # إنشاء المهمة
        task = cls(
            group_id=schedule.group_id,
            task_type=task_type,
            scheduled_time=datetime.now(SCHEDULER_TIMEZONE),
            deadline_minutes=deadline_minutes,
            is_sent=True,
            sent_at=datetime.now(SCHEDULER_TIMEZONE),
            message_id=message_id,
            message=message,
            points=points,
            schedule_id=schedule_id
        )
        
        db.session.add(task)
        db.session.commit()
        
        return task
        
    def is_active(self):
        """التحقق مما إذا كانت المهمة نشطة (لم تنتهي مهلتها)"""
        return not self.is_expired()
        
    def has_user_joined(self, user_id):
        """التحقق مما إذا كان المستخدم قد انضم للمهمة"""
        # الحصول على مشارك المجموعة
        participant = GroupTaskParticipant.query.filter_by(
            group_id=self.group_id,
            user_id=user_id
        ).first()
        
        if not participant:
            return False
            
        # التحقق من وجود مشاركة في المهمة
        from study_bot.models.group import GroupTaskParticipation
        participation = GroupTaskParticipation.query.filter_by(
            task_id=self.id,
            participant_id=participant.id
        ).first()
        
        return participation is not None
        
    def add_participant(self, user_id):
        """إضافة مشارك للمهمة"""
        if self.is_expired():
            return False
            
        # الحصول على مشارك المجموعة
        participant = GroupTaskParticipant.get_or_create(
            group_id=self.group_id,
            user_id=user_id
        )
        
        if not participant:
            return False
            
        # التحقق من وجود مشاركة سابقة
        if self.has_user_joined(user_id):
            return True
            
        # إنشاء مشاركة جديدة
        participation = GroupTaskParticipation(
            task_id=self.id,
            participant_id=participant.id
        )
        
        # تحديث إحصائيات المشارك
        participant.daily_completion_count += 1
        participant.total_completion_count += 1
        participant.last_completion_date = datetime.now(SCHEDULER_TIMEZONE)
        
        # حفظ التغييرات
        db.session.add(participation)
        db.session.commit()
        
        return True
    
    def is_expired(self):
        """التحقق مما إذا كانت المهمة منتهية الصلاحية"""
        if not self.sent_at:
            return False
        
        now = datetime.now(SCHEDULER_TIMEZONE)
        deadline = self.sent_at + timedelta(minutes=self.deadline_minutes)
        
        return now > deadline
    
    def get_remaining_time(self):
        """الحصول على الوقت المتبقي للمهمة بالثواني"""
        if not self.sent_at or self.is_expired():
            return 0
        
        now = datetime.now(SCHEDULER_TIMEZONE)
        deadline = self.sent_at + timedelta(minutes=self.deadline_minutes)
        
        return max(0, int((deadline - now).total_seconds()))
    
    def get_completion_count(self):
        """الحصول على عدد المستخدمين الذين أكملوا المهمة"""
        from study_bot.models import GroupTaskParticipation
        return GroupTaskParticipation.query.filter_by(task_id=self.id).count()
    
    def __repr__(self):
        return f'<GroupTaskTracker {self.group_id} - {self.task_type}>'


class GroupTaskParticipant(db.Model):
    """نموذج مشارك مهام المجموعة"""
    __tablename__ = 'group_task_participant'
    
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey('group.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    schedule_type = Column(String(20), nullable=False, default='morning')  # morning, evening, custom
    join_date = Column(DateTime, default=datetime.now(SCHEDULER_TIMEZONE))
    is_active = Column(Boolean, default=True)
    last_completion_date = Column(DateTime, nullable=True)
    
    # إحصائيات
    daily_completion_count = Column(Integer, default=0)
    total_completion_count = Column(Integer, default=0)
    
    # دالة للحصول على مشارك مجموعة أو إنشائه إذا لم يكن موجودًا
    @classmethod
    def get_or_create(cls, group_id, user_id, schedule_type='morning'):
        """الحصول على مشارك مجموعة أو إنشائه إذا لم يكن موجودًا"""
        instance = cls.query.filter_by(group_id=group_id, user_id=user_id).first()
        if not instance:
            instance = cls(group_id=group_id, user_id=user_id, schedule_type=schedule_type)
            db.session.add(instance)
            db.session.commit()
        return instance
    
    # دالة لإعادة ضبط العدادات اليومية
    def reset_daily_stats(self):
        """إعادة ضبط الإحصائيات اليومية"""
        self.daily_completion_count = 0
        db.session.commit()
    
    def __repr__(self):
        return f'<GroupTaskParticipant {self.group_id} - {self.user_id}>'


class GroupTaskParticipation(db.Model):
    """نموذج مشاركة مهمة مجموعة"""
    __tablename__ = 'group_task_participation'
    
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey('group_task_tracker.id'), nullable=False)
    participant_id = Column(Integer, ForeignKey('group_task_participant.id'), nullable=False)
    completion_time = Column(DateTime, default=datetime.now(SCHEDULER_TIMEZONE))
    
    def __repr__(self):
        return f'<GroupTaskParticipation {self.task_id} - {self.participant_id}>'


class MotivationalMessage(db.Model):
    """نموذج الرسائل التحفيزية"""
    __tablename__ = 'motivational_message'
    
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey('group.id'), nullable=False)
    message = Column(Text, nullable=False)
    sent_at = Column(DateTime, default=datetime.now(SCHEDULER_TIMEZONE))
    message_id = Column(Integer, nullable=True)
    
    def __repr__(self):
        return f'<MotivationalMessage {self.group_id} - {self.id}>'