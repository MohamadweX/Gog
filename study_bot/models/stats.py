"""
نماذج الإحصائيات
يحتوي على تعريف نماذج الإحصائيات المختلفة
"""

from datetime import datetime, timedelta
import pytz
import json
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text, ForeignKey, func
from sqlalchemy.orm import relationship

from study_bot.config import SCHEDULER_TIMEZONE
from study_bot.models import db

class SystemStats(db.Model):
    """نموذج إحصائيات النظام"""
    __tablename__ = 'system_stats'
    
    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.now(SCHEDULER_TIMEZONE), onupdate=datetime.now(SCHEDULER_TIMEZONE))
    
    @classmethod
    def get_value(cls, key, default=None):
        """الحصول على قيمة إحصائية"""
        stat = cls.query.filter_by(key=key).first()
        if not stat:
            return default
        
        try:
            # محاولة تحويل القيمة إلى عدد إذا كانت تبدو كذلك
            if stat.value.isdigit():
                return int(stat.value)
            elif stat.value.replace('.', '', 1).isdigit():
                return float(stat.value)
            
            # محاولة تحليل القيمة كـ JSON
            return json.loads(stat.value)
        except:
            return stat.value
    
    @classmethod
    def set_value(cls, key, value):
        """تعيين قيمة إحصائية"""
        stat = cls.query.filter_by(key=key).first()
        
        # تحويل القيمة إلى نص إذا لم تكن كذلك
        if not isinstance(value, str):
            if isinstance(value, (dict, list, tuple)):
                value = json.dumps(value)
            else:
                value = str(value)
        
        if not stat:
            stat = cls(key=key, value=value)
            db.session.add(stat)
        else:
            stat.value = value
        
        db.session.commit()
        return stat
    
    @classmethod
    def increment(cls, key, amount=1):
        """زيادة قيمة إحصائية عددية"""
        stat = cls.query.filter_by(key=key).first()
        
        if not stat:
            stat = cls(key=key, value=str(amount))
            db.session.add(stat)
        else:
            try:
                current_value = int(stat.value)
                stat.value = str(current_value + amount)
            except:
                stat.value = str(amount)
        
        db.session.commit()
        return stat
    
    @classmethod
    def get_all_stats(cls):
        """الحصول على جميع الإحصائيات"""
        stats = {}
        for stat in cls.query.all():
            stats[stat.key] = cls.get_value(stat.key)
        
        return stats
    
    def __repr__(self):
        return f'<SystemStats {self.key} = {self.value}>'


class DailyStats(db.Model):
    """نموذج الإحصائيات اليومية"""
    __tablename__ = 'daily_stats'
    
    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False)
    key = Column(String(100), nullable=False)
    value = Column(Integer, default=0)
    
    # إنشاء فهرس مركب على الحقول التاريخ والمفتاح
    __table_args__ = (
        db.UniqueConstraint('date', 'key', name='uq_daily_stats_date_key'),
    )
    
    @classmethod
    def get_value(cls, key, date=None):
        """الحصول على قيمة إحصائية يومية"""
        if not date:
            date = datetime.now(SCHEDULER_TIMEZONE).replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        stat = cls.query.filter_by(key=key, date=date).first()
        return stat.value if stat else 0
    
    @classmethod
    def set_value(cls, key, value, date=None):
        """تعيين قيمة إحصائية يومية"""
        if not date:
            date = datetime.now(SCHEDULER_TIMEZONE).replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        stat = cls.query.filter_by(key=key, date=date).first()
        
        if not stat:
            stat = cls(key=key, value=value, date=date)
            db.session.add(stat)
        else:
            stat.value = value
        
        db.session.commit()
        return stat
    
    @classmethod
    def increment(cls, key, amount=1, date=None):
        """زيادة قيمة إحصائية يومية"""
        if not date:
            date = datetime.now(SCHEDULER_TIMEZONE).replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        stat = cls.query.filter_by(key=key, date=date).first()
        
        if not stat:
            stat = cls(key=key, value=amount, date=date)
            db.session.add(stat)
        else:
            stat.value += amount
        
        db.session.commit()
        return stat
    
    @classmethod
    def get_daily_stats(cls, date=None):
        """الحصول على إحصائيات يوم محدد"""
        if not date:
            date = datetime.now(SCHEDULER_TIMEZONE).replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        stats = {}
        for stat in cls.query.filter_by(date=date).all():
            stats[stat.key] = stat.value
        
        return stats
    
    @classmethod
    def get_stats_range(cls, key, start_date, end_date=None):
        """الحصول على إحصائيات خلال فترة زمنية"""
        if not end_date:
            end_date = datetime.now(SCHEDULER_TIMEZONE)
        
        # التأكد من أن التواريخ في بداية اليوم
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # الحصول على الإحصائيات خلال الفترة المحددة
        stats = cls.query.filter(
            cls.key == key,
            cls.date >= start_date,
            cls.date <= end_date
        ).order_by(cls.date).all()
        
        # تنظيم البيانات حسب التاريخ
        result = {}
        for stat in stats:
            date_str = stat.date.strftime('%Y-%m-%d')
            result[date_str] = stat.value
        
        return result
    
    def __repr__(self):
        return f'<DailyStats {self.date.strftime("%Y-%m-%d")} {self.key} = {self.value}>'