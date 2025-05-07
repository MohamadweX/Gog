"""
نموذج المستخدم
يحتوي على تعريف نموذج المستخدم وخصائصه
"""

from datetime import datetime, timedelta
import pytz
import json
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text, ForeignKey, func
from sqlalchemy.orm import relationship
from flask_login import UserMixin

from study_bot.config import SCHEDULER_TIMEZONE
from study_bot.models import db

class User(UserMixin, db.Model):
    """نموذج المستخدم"""
    __tablename__ = 'user'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    registration_date = Column(DateTime, default=datetime.now(SCHEDULER_TIMEZONE))
    last_activity = Column(DateTime, default=datetime.now(SCHEDULER_TIMEZONE))
    language_code = Column(String(10), default='ar')
    
    # إحصائيات المستخدم
    points = Column(Integer, default=0)
    streak_days = Column(Integer, default=0)
    streak_start_date = Column(DateTime, nullable=True)
    last_streak_update = Column(DateTime, nullable=True)
    total_tasks_completed = Column(Integer, default=0)
    total_messages_sent = Column(Integer, default=0)
    total_messages_received = Column(Integer, default=0)
    
    # علاقات
    group_participations = relationship('GroupTaskParticipant', backref='user', lazy=True)
    activity_log = relationship('UserActivityLog', backref='user', lazy=True)
    
    def get_full_name(self):
        """الحصول على الاسم الكامل للمستخدم"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.username:
            return self.username
        else:
            return f"المستخدم {self.telegram_id}"
    
    def update_activity(self):
        """تحديث آخر نشاط للمستخدم"""
        self.last_activity = datetime.now(SCHEDULER_TIMEZONE)
        db.session.commit()
    
    def update_streak(self):
        """تحديث سلسلة أيام النشاط المتتالية"""
        now = datetime.now(SCHEDULER_TIMEZONE)
        today = now.date()
        
        # إذا كانت هذه أول مرة يتم فيها تحديث السلسلة
        if not self.last_streak_update:
            self.streak_days = 1
            self.streak_start_date = now
            self.last_streak_update = now
            db.session.commit()
            return 1
        
        # الحصول على تاريخ آخر تحديث
        last_update = self.last_streak_update.date()
        
        # إذا كان آخر تحديث كان اليوم، فلا داعي للتحديث
        if last_update == today:
            return self.streak_days
        
        # إذا كان آخر تحديث كان بالأمس، فزيادة السلسلة
        if (today - last_update).days == 1:
            self.streak_days += 1
        # إذا مر أكثر من يوم، فإعادة ضبط السلسلة
        else:
            self.streak_days = 1
            self.streak_start_date = now
        
        self.last_streak_update = now
        db.session.commit()
        return self.streak_days
    
    def log_activity(self, activity_type, details=None):
        """تسجيل نشاط المستخدم"""
        log = UserActivityLog(
            user_id=self.id,
            activity_type=activity_type,
            details=json.dumps(details) if details else None,
            timestamp=datetime.now(SCHEDULER_TIMEZONE)
        )
        db.session.add(log)
        db.session.commit()
    
    def get_group_participation_summary(self):
        """الحصول على ملخص مشاركة المستخدم في المجموعات"""
        from study_bot.models import GroupTaskParticipant
        
        participations = GroupTaskParticipant.query.filter_by(user_id=self.id, is_active=True).all()
        
        summary = {
            'morning_groups': 0,
            'evening_groups': 0,
            'total_completions': 0,
            'groups': []
        }
        
        for participation in participations:
            if participation.schedule_type == 'morning':
                summary['morning_groups'] += 1
            elif participation.schedule_type == 'evening':
                summary['evening_groups'] += 1
            
            summary['total_completions'] += participation.total_completion_count
            
            group_info = {
                'group_id': participation.group_id,
                'schedule_type': participation.schedule_type,
                'completions': participation.total_completion_count,
                'daily_completions': participation.daily_completion_count,
                'last_completion': participation.last_completion_date.isoformat() if participation.last_completion_date else None
            }
            
            summary['groups'].append(group_info)
        
        return summary
    
    def get_camp_participation_summary(self):
        """الحصول على ملخص مشاركة المستخدم في المعسكرات"""
        from study_bot.models import CampParticipant, CustomCamp
        
        participations = db.session.query(
            CampParticipant, CustomCamp
        ).join(
            CustomCamp, CampParticipant.camp_id == CustomCamp.id
        ).filter(
            CampParticipant.user_id == self.id,
            CampParticipant.is_active == True,
            CustomCamp.is_active == True
        ).all()
        
        summary = {
            'active_camps': 0,
            'total_points': 0,
            'camps': []
        }
        
        for participant, camp in participations:
            summary['active_camps'] += 1
            summary['total_points'] += participant.total_points
            
            now = datetime.now(SCHEDULER_TIMEZONE)
            progress = 0
            if camp.start_date and camp.end_date:
                total_days = (camp.end_date - camp.start_date).days
                if total_days > 0:
                    days_passed = (now - camp.start_date).days
                    progress = min(100, max(0, int(days_passed / total_days * 100)))
            
            camp_info = {
                'camp_id': camp.id,
                'camp_name': camp.name,
                'points': participant.total_points,
                'join_date': participant.join_date.isoformat() if participant.join_date else None,
                'progress': progress
            }
            
            summary['camps'].append(camp_info)
        
        return summary
    
    def add_points(self, points):
        """إضافة نقاط للمستخدم"""
        if points <= 0:
            return self.points
            
        self.points += points
        db.session.commit()
        
        # تسجيل النشاط
        self.log_activity('add_points', {'points': points, 'total': self.points})
        
        # تحديث سلسلة النشاط
        self.update_streak()
        
        return self.points
        
    def increment_tasks_completed(self):
        """زيادة عدد المهام المكتملة"""
        self.total_tasks_completed += 1
        db.session.commit()
        
        # تسجيل النشاط
        self.log_activity('complete_task', {'total': self.total_tasks_completed})
        
        return self.total_tasks_completed
    
    
    @classmethod
    def get_or_create(cls, telegram_id, username=None, first_name=None, last_name=None):
        # Get user or create if not exists
        from study_bot.models import db
        from study_bot.config import logger
        
        user = cls.query.filter_by(telegram_id=telegram_id).first()
        
        if not user:
            user = cls(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name
            )
            db.session.add(user)
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error adding user: {e}")
                raise
        
        return user
        
    def __repr__(self):
        return f'<User {self.get_full_name()}>'


class UserActivityLog(db.Model):
    """نموذج سجل نشاط المستخدم"""
    __tablename__ = 'user_activity_log'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    activity_type = Column(String(50), nullable=False)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.now(SCHEDULER_TIMEZONE))
    
    def __repr__(self):
        return f'<UserActivityLog {self.activity_type} - {self.timestamp}>'