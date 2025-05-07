"""
نماذج المعسكرات
يحتوي على تعريف نماذج المعسكرات الدراسية المخصصة
"""

from datetime import datetime, timedelta
import pytz
import json
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text, ForeignKey, func
from sqlalchemy.orm import relationship

from study_bot.config import SCHEDULER_TIMEZONE
from study_bot.models import db

class CustomCamp(db.Model):
    """نموذج المعسكر الدراسي المخصص"""
    __tablename__ = 'custom_camp'
    
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey('group.id'), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    created_by = Column(Integer, nullable=False)  # معرف مشرف تيليجرام
    creation_date = Column(DateTime, default=datetime.now(SCHEDULER_TIMEZONE))
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    max_participants = Column(Integer, default=0)  # 0 يعني غير محدود
    is_active = Column(Boolean, default=True)
    announcement_message_id = Column(Integer, nullable=True)  # معرف رسالة الإعلان
    
    # علاقات
    tasks = relationship('CampTask', backref='camp', lazy=True)
    participants = relationship('CampParticipant', backref='camp', lazy=True)
    
    def is_expired(self):
        """التحقق مما إذا كان المعسكر منتهي الصلاحية"""
        return datetime.now(SCHEDULER_TIMEZONE) > self.end_date
    
    def is_joinable(self):
        """التحقق مما إذا كان يمكن الانضمام إلى المعسكر"""
        if not self.is_active or self.is_expired():
            return False
        
        if self.max_participants == 0:
            return True
        
        # التحقق من عدد المشاركين الحاليين
        current_participants = CampParticipant.query.filter_by(
            camp_id=self.id,
            is_active=True
        ).count()
        
        return current_participants < self.max_participants
    
    def get_active_participants(self):
        """الحصول على المشاركين النشطين في المعسكر"""
        return CampParticipant.query.filter_by(
            camp_id=self.id,
            is_active=True
        ).all()
    
    def get_active_tasks(self):
        """الحصول على المهام النشطة في المعسكر"""
        now = datetime.now(SCHEDULER_TIMEZONE)
        
        return CampTask.query.filter_by(
            camp_id=self.id
        ).filter(
            CampTask.scheduled_time <= now,
            CampTask.scheduled_time >= (now - timedelta(days=1))
        ).order_by(CampTask.scheduled_time).all()
    
    def get_upcoming_tasks(self, limit=5):
        """الحصول على المهام القادمة في المعسكر"""
        now = datetime.now(SCHEDULER_TIMEZONE)
        
        return CampTask.query.filter_by(
            camp_id=self.id
        ).filter(
            CampTask.scheduled_time > now
        ).order_by(CampTask.scheduled_time).limit(limit).all()
    
    def get_stats(self):
        """الحصول على إحصائيات المعسكر"""
        total_participants = CampParticipant.query.filter_by(
            camp_id=self.id,
            is_active=True
        ).count()
        
        total_tasks = CampTask.query.filter_by(
            camp_id=self.id
        ).count()
        
        sent_tasks = CampTask.query.filter_by(
            camp_id=self.id,
            is_sent=True
        ).count()
        
        # إجمالي نقاط المشاركين
        total_points = db.session.query(
            func.sum(CampParticipant.total_points)
        ).filter_by(
            camp_id=self.id,
            is_active=True
        ).scalar() or 0
        
        # متوسط نقاط المشاركين
        avg_points = total_points / total_participants if total_participants > 0 else 0
        
        # المدة المتبقية بالأيام
        now = datetime.now(SCHEDULER_TIMEZONE)
        remaining_days = (self.end_date - now).days + 1 if now < self.end_date else 0
        
        # نسبة التقدم
        total_days = (self.end_date - self.start_date).days + 1
        progress = int((total_days - remaining_days) / total_days * 100) if total_days > 0 else 0
        
        return {
            'total_participants': total_participants,
            'total_tasks': total_tasks,
            'sent_tasks': sent_tasks,
            'total_points': total_points,
            'avg_points': avg_points,
            'remaining_days': remaining_days,
            'progress': min(100, max(0, progress)),
            'start_date': self.start_date.strftime('%Y-%m-%d'),
            'end_date': self.end_date.strftime('%Y-%m-%d')
        }
    
    def __repr__(self):
        return f'<CustomCamp {self.name}>'


class CampTask(db.Model):
    """نموذج مهمة المعسكر"""
    __tablename__ = 'camp_task'
    
    id = Column(Integer, primary_key=True)
    camp_id = Column(Integer, ForeignKey('custom_camp.id'), nullable=False)
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    scheduled_time = Column(DateTime, nullable=False)
    points = Column(Integer, default=1)
    deadline_minutes = Column(Integer, default=10)
    is_sent = Column(Boolean, default=False)
    sent_at = Column(DateTime, nullable=True)
    message_id = Column(Integer, nullable=True)  # معرف رسالة المهمة
    
    # علاقات
    participations = relationship('CampTaskParticipation', backref='task', lazy=True)
    
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
    
    def get_participation_count(self):
        """الحصول على عدد المشاركين في المهمة"""
        return CampTaskParticipation.query.filter_by(
            task_id=self.id
        ).count()
    
    def __repr__(self):
        return f'<CampTask {self.title}>'


class CampParticipant(db.Model):
    """نموذج مشارك المعسكر"""
    __tablename__ = 'camp_participant'
    
    id = Column(Integer, primary_key=True)
    camp_id = Column(Integer, ForeignKey('custom_camp.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    join_date = Column(DateTime, default=datetime.now(SCHEDULER_TIMEZONE))
    is_active = Column(Boolean, default=True)
    total_points = Column(Integer, default=0)
    
    # علاقات
    participations = relationship('CampTaskParticipation', backref='camp_participant', lazy=True)
    user_details = relationship('User', foreign_keys=[user_id], backref='camp_user_details', lazy=True)
    
    def get_completion_percentage(self):
        """الحصول على نسبة إكمال المهام"""
        camp = CustomCamp.query.get(self.camp_id)
        if not camp:
            return 0
        
        # إجمالي المهام المرسلة في المعسكر
        total_sent_tasks = CampTask.query.filter_by(
            camp_id=self.camp_id,
            is_sent=True
        ).count()
        
        if total_sent_tasks == 0:
            return 0
        
        # عدد المهام التي أكملها المشارك
        completed_tasks = CampTaskParticipation.query.filter_by(
            participant_id=self.id
        ).count()
        
        return min(100, int(completed_tasks / total_sent_tasks * 100))
    
    def get_rank(self):
        """الحصول على ترتيب المشارك في المعسكر"""
        # الحصول على جميع المشاركين مرتبين حسب النقاط
        participants = CampParticipant.query.filter_by(
            camp_id=self.camp_id,
            is_active=True
        ).order_by(CampParticipant.total_points.desc()).all()
        
        for i, participant in enumerate(participants):
            if participant.id == self.id:
                return i + 1
        
        return 0
    
    def __repr__(self):
        return f'<CampParticipant {self.id}>'


class CampTaskParticipation(db.Model):
    """نموذج مشاركة في مهمة معسكر"""
    __tablename__ = 'camp_task_participation'
    
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey('camp_task.id'), nullable=False)
    participant_id = Column(Integer, ForeignKey('camp_participant.id'), nullable=False)
    participation_time = Column(DateTime, default=datetime.now(SCHEDULER_TIMEZONE))
    points_earned = Column(Integer, default=0)
    
    def __repr__(self):
        return f'<CampTaskParticipation {self.id}>'