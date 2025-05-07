"""
نماذج الإشعارات
يحتوي على تعريفات قاعدة البيانات المتعلقة بالإشعارات وسجلات الرسائل
"""

import pytz
import sqlalchemy as sa
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta

from study_bot.models import db


class BotNotification(db.Model):
    """نموذج إشعارات البوت"""
    __tablename__ = 'bot_notification'
    
    id = sa.Column(sa.Integer, primary_key=True)
    user_id = sa.Column(sa.Integer, sa.ForeignKey('user.id'), nullable=False)
    message = sa.Column(sa.Text, nullable=False)
    scheduled_time = sa.Column(sa.DateTime, nullable=False)
    sent = sa.Column(sa.Boolean, default=False)
    sent_at = sa.Column(sa.DateTime, nullable=True)
    notification_type = sa.Column(sa.String(50), nullable=False)  # نوع الإشعار
    data = sa.Column(sa.Text, nullable=True)  # بيانات إضافية (JSON)
    
    # العلاقات
    user = relationship('User', backref='notifications')
    
    def __repr__(self):
        return f"<BotNotification {self.id} for user {self.user_id}>"
    
    def mark_as_sent(self):
        """تحديد الإشعار كمرسل"""
        self.sent = True
        self.sent_at = datetime.now(pytz.UTC)
        db.session.commit()
    
    def is_expired(self):
        """التحقق مما إذا كان الإشعار قد انتهى وقته"""
        now = datetime.now(pytz.UTC)
        return now > self.scheduled_time + timedelta(minutes=30)


class MessageLog(db.Model):
    """نموذج سجل الرسائل"""
    __tablename__ = 'message_log'
    
    id = sa.Column(sa.Integer, primary_key=True)
    user_id = sa.Column(sa.Integer, sa.ForeignKey('user.id'), nullable=True)
    chat_id = sa.Column(sa.BigInteger, nullable=False)
    message_id = sa.Column(sa.Integer, nullable=True)
    message_type = sa.Column(sa.String(50), nullable=False)  # نوع الرسالة (رسالة، إشعار، رد، إلخ)
    content = sa.Column(sa.Text, nullable=True)
    sent_at = sa.Column(sa.DateTime, default=lambda: datetime.now(pytz.UTC))
    is_from_bot = sa.Column(sa.Boolean, default=True)  # هل الرسالة من البوت أم من المستخدم
    
    # العلاقات
    user = relationship('User', backref='messages')
    
    def __repr__(self):
        return f"<MessageLog {self.id} in chat {self.chat_id}>"


class UserSession(db.Model):
    """نموذج جلسة المستخدم"""
    __tablename__ = 'user_session'
    
    id = sa.Column(sa.Integer, primary_key=True)
    user_id = sa.Column(sa.Integer, sa.ForeignKey('user.id'), nullable=False)
    state = sa.Column(sa.String(50), nullable=True)  # حالة المحادثة الحالية
    data = sa.Column(sa.Text, nullable=True)  # بيانات الجلسة (JSON)
    started_at = sa.Column(sa.DateTime, default=lambda: datetime.now(pytz.UTC))
    last_interaction = sa.Column(sa.DateTime, default=lambda: datetime.now(pytz.UTC))
    
    # العلاقات
    user = relationship('User', backref='sessions')
    
    def __repr__(self):
        return f"<UserSession {self.id} for user {self.user_id}>"
    
    def update_last_interaction(self):
        """تحديث وقت آخر تفاعل"""
        self.last_interaction = datetime.now(pytz.UTC)
        db.session.commit()
    
    def update_state(self, state):
        """تحديث حالة المحادثة"""
        self.state = state
        self.last_interaction = datetime.now(pytz.UTC)
        db.session.commit()
    
    def is_expired(self):
        """التحقق مما إذا كانت الجلسة منتهية الصلاحية"""
        now = datetime.now(pytz.UTC)
        return now > self.last_interaction + timedelta(minutes=30)
    
    def reset(self):
        """إعادة تعيين حالة الجلسة"""
        self.state = None
        self.data = None
        self.last_interaction = datetime.now(pytz.UTC)
        db.session.commit()