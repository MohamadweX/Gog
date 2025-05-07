"""
نماذج قاعدة البيانات للمعسكرات الدراسية
تحتوي على تعريفات للجداول المرتبطة بالمعسكرات الدراسية المخصصة
"""

from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, Boolean, DateTime, BigInteger, ForeignKey, Text, Float
from sqlalchemy.orm import relationship

from study_bot.models import db


class CustomCamp(db.Model):
    """نموذج لتخزين معلومات المعسكرات الدراسية المخصصة"""
    
    __tablename__ = 'custom_camp'
    
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey('group.id'), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    created_by = Column(BigInteger, nullable=False)  # معرف مشرف تيليجرام
    creation_date = Column(DateTime, default=datetime.utcnow)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    max_participants = Column(Integer, default=0)  # 0 يعني غير محدود
    is_active = Column(Boolean, default=True)
    announcement_message_id = Column(Integer, nullable=True)  # معرف رسالة الإعلان
    
    # العلاقات
    tasks = relationship('CampTask', backref='camp', lazy=True)
    participants = relationship('CampParticipant', backref='camp', lazy=True)
    
    def __repr__(self):
        return f"<CustomCamp '{self.name}' for group {self.group_id}>"


class CampTask(db.Model):
    """نموذج لتخزين مهام المعسكرات"""
    
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
    
    # العلاقات
    participations = relationship('CampTaskParticipation', backref='task', lazy=True)
    
    def __repr__(self):
        return f"<CampTask '{self.title}' for camp {self.camp_id}>"


class CampParticipant(db.Model):
    """نموذج لتخزين مشاركي المعسكرات"""
    
    __tablename__ = 'camp_participant'
    
    id = Column(Integer, primary_key=True)
    camp_id = Column(Integer, ForeignKey('custom_camp.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    join_date = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    total_points = Column(Integer, default=0)
    
    # العلاقات
    participations = relationship('CampTaskParticipation', backref='participant', lazy=True)
    
    def __repr__(self):
        return f"<CampParticipant user={self.user_id} in camp {self.camp_id}>"


class CampTaskParticipation(db.Model):
    """نموذج لتخزين مشاركات المستخدمين في مهام المعسكرات"""
    
    __tablename__ = 'camp_task_participation'
    
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey('camp_task.id'), nullable=False)
    participant_id = Column(Integer, ForeignKey('camp_participant.id'), nullable=False)
    participation_time = Column(DateTime, default=datetime.utcnow)
    points_earned = Column(Integer, default=0)
    
    def __repr__(self):
        return f"<CampTaskParticipation participant={self.participant_id} in task {self.task_id}>"