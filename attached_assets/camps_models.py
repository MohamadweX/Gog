#!/usr/bin/env python3
"""
نماذج قاعدة البيانات للمعسكرات الدراسية
تحتوي على تعريفات للجداول المرتبطة بالمعسكرات الدراسية المخصصة
"""

from datetime import datetime, timedelta
from study_bot.models import db


class CustomCamp(db.Model):
    """نموذج لتخزين معلومات المعسكرات الدراسية المخصصة"""
    
    __tablename__ = 'custom_camp'
    
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_by = db.Column(db.BigInteger, nullable=False)  # معرف مشرف تيليجرام
    creation_date = db.Column(db.DateTime, default=datetime.utcnow)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    max_participants = db.Column(db.Integer, default=0)  # 0 يعني غير محدود
    is_active = db.Column(db.Boolean, default=True)
    announcement_message_id = db.Column(db.Integer, nullable=True)  # معرف رسالة الإعلان
    
    # العلاقات
    tasks = db.relationship('CampTask', backref='camp', lazy=True)
    participants = db.relationship('CampParticipant', backref='camp', lazy=True)
    
    def __repr__(self):
        return f"<CustomCamp '{self.name}' for group {self.group_id}>"


class CampTask(db.Model):
    """نموذج لتخزين مهام المعسكرات"""
    
    __tablename__ = 'camp_task'
    
    id = db.Column(db.Integer, primary_key=True)
    camp_id = db.Column(db.Integer, db.ForeignKey('custom_camp.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    scheduled_time = db.Column(db.DateTime, nullable=False)
    points = db.Column(db.Integer, default=1)
    deadline_minutes = db.Column(db.Integer, default=10)
    is_sent = db.Column(db.Boolean, default=False)
    sent_at = db.Column(db.DateTime, nullable=True)
    message_id = db.Column(db.Integer, nullable=True)  # معرف رسالة المهمة
    
    # العلاقات
    participations = db.relationship('CampTaskParticipation', backref='task', lazy=True)
    
    def __repr__(self):
        return f"<CampTask '{self.title}' for camp {self.camp_id}>"


class CampParticipant(db.Model):
    """نموذج لتخزين مشاركي المعسكرات"""
    
    __tablename__ = 'camp_participant'
    
    id = db.Column(db.Integer, primary_key=True)
    camp_id = db.Column(db.Integer, db.ForeignKey('custom_camp.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    join_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    total_points = db.Column(db.Integer, default=0)
    
    # العلاقات
    participations = db.relationship('CampTaskParticipation', backref='participant', lazy=True)
    
    def __repr__(self):
        return f"<CampParticipant user={self.user_id} in camp {self.camp_id}>"


class CampTaskParticipation(db.Model):
    """نموذج لتخزين مشاركات المستخدمين في مهام المعسكرات"""
    
    __tablename__ = 'camp_task_participation'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('camp_task.id'), nullable=False)
    participant_id = db.Column(db.Integer, db.ForeignKey('camp_participant.id'), nullable=False)
    participation_time = db.Column(db.DateTime, default=datetime.utcnow)
    points_earned = db.Column(db.Integer, default=0)
    
    def __repr__(self):
        return f"<CampTaskParticipation participant={self.participant_id} in task {self.task_id}>"
