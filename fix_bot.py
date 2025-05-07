#!/usr/bin/env python3
"""
سكريبت لإصلاح مشاكل البوت
"""

import os
import sys
import time
from flask import Flask
from sqlalchemy import text, inspect, Column, String, Boolean
import logging

# تكوين التسجيل
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('bot_fixer')

# إنشاء تطبيق فلاسك
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# دالة لإضافة دالة get_or_create لنموذج المستخدم
def add_get_or_create_method():
    """إضافة دالة get_or_create لنموذج المستخدم"""
    logger.info("إضافة دالة get_or_create لنموذج المستخدم")
    
    try:
        user_model_path = 'study_bot/models/user.py'
        with open(user_model_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # التحقق مما إذا كانت الدالة موجودة بالفعل
        if '@classmethod\n    def get_or_create(' in content:
            logger.info("دالة get_or_create موجودة بالفعل")
            return True
        
        # تحديد موقع إضافة الدالة - قبل دالة __repr__
        repr_position = content.find('def __repr__(self):')
        if repr_position > 0:
            # إعداد نص الدالة
            get_or_create_method = """
    @classmethod
    def get_or_create(cls, telegram_id, username=None, first_name=None, last_name=None):
        """الحصول على المستخدم أو إنشاؤه إذا لم يكن موجودًا"""
        from study_bot.models import db
        
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
                logger.error(f"خطأ في إضافة المستخدم: {e}")
                raise
        
        return user
"""
            
            # تقسيم المحتوى وإضافة الدالة
            before_repr = content[:repr_position]
            after_repr = content[repr_position:]
            
            new_content = before_repr + get_or_create_method + after_repr
            
            # حفظ الملف المعدل
            with open(user_model_path, 'w', encoding='utf-8') as file:
                file.write(new_content)
            
            logger.info("تمت إضافة دالة get_or_create للمستخدم بنجاح")
            return True
        else:
            logger.error("لم يتم العثور على موقع مناسب لإضافة الدالة")
            return False
    
    except Exception as e:
        logger.error(f"حدث خطأ أثناء إضافة دالة get_or_create: {e}")
        return False

# دالة لإصلاح مشكلة عمود username
def fix_group_model():
    """إصلاح مشكلة عمود username في نموذج المجموعة"""
    logger.info("إصلاح مشكلة عمود username في نموذج المجموعة")
    
    try:
        group_model_path = 'study_bot/models/group.py'
        with open(group_model_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # البحث عن تعريف عمود username
        username_column_exists = 'username = Column(String' in content
        
        if username_column_exists:
            logger.info("عمود username موجود بالفعل في نموذج المجموعة")
        else:
            # إضافة عمود username بعد عمود telegram_id
            telegram_id_position = content.find('telegram_id = Column(Integer')
            if telegram_id_position > 0:
                # العثور على نهاية التعريف
                line_end = content.find('\n', telegram_id_position)
                
                # إنشاء تعريف عمود username
                username_column = '\n    username = Column(String(100), nullable=True)'
                
                # إضافة العمود بعد telegram_id
                new_content = content[:line_end] + username_column + content[line_end:]
                
                # حفظ الملف المعدل
                with open(group_model_path, 'w', encoding='utf-8') as file:
                    file.write(new_content)
                
                logger.info("تمت إضافة عمود username إلى نموذج المجموعة")
            else:
                logger.error("لم يتم العثور على عمود telegram_id في نموذج المجموعة")
        
        return True
    
    except Exception as e:
        logger.error(f"حدث خطأ أثناء إصلاح نموذج المجموعة: {e}")
        return False

# دالة لإصلاح قاعدة البيانات
def fix_database():
    """إصلاح قاعدة البيانات"""
    logger.info("إصلاح قاعدة البيانات")
    
    from flask_sqlalchemy import SQLAlchemy
    db = SQLAlchemy(app)
    
    with app.app_context():
        try:
            # التحقق من وجود الأعمدة
            inspector = inspect(db.engine)
            group_columns = [col['name'] for col in inspector.get_columns('group')]
            
            # فتح اتصال لتنفيذ استعلامات SQL
            conn = db.engine.connect()
            transaction = conn.begin()
            
            try:
                # إضافة العمود username إذا لم يكن موجوداً
                if 'username' not in group_columns:
                    conn.execute(text('ALTER TABLE "group" ADD COLUMN username VARCHAR(100);'))
                    logger.info("تمت إضافة عمود username إلى جدول group")
                
                # إضافة الأعمدة المطلوبة للجدول
                if 'morning_schedule_enabled' not in group_columns:
                    conn.execute(text('ALTER TABLE "group" ADD COLUMN morning_schedule_enabled BOOLEAN DEFAULT FALSE;'))
                    logger.info("تمت إضافة عمود morning_schedule_enabled إلى جدول group")
                
                if 'evening_schedule_enabled' not in group_columns:
                    conn.execute(text('ALTER TABLE "group" ADD COLUMN evening_schedule_enabled BOOLEAN DEFAULT FALSE;'))
                    logger.info("تمت إضافة عمود evening_schedule_enabled إلى جدول group")
                
                if 'custom_schedule_enabled' not in group_columns:
                    conn.execute(text('ALTER TABLE "group" ADD COLUMN custom_schedule_enabled BOOLEAN DEFAULT FALSE;'))
                    logger.info("تمت إضافة عمود custom_schedule_enabled إلى جدول group")
                
                if 'motivation_enabled' not in group_columns:
                    conn.execute(text('ALTER TABLE "group" ADD COLUMN motivation_enabled BOOLEAN DEFAULT TRUE;'))
                    logger.info("تمت إضافة عمود motivation_enabled إلى جدول group")
                
                # حفظ التغييرات
                transaction.commit()
                logger.info("تم حفظ التغييرات في قاعدة البيانات بنجاح")
                return True
            
            except Exception as e:
                transaction.rollback()
                logger.error(f"حدث خطأ أثناء تحديث قاعدة البيانات: {e}")
                return False
            
            finally:
                conn.close()
        
        except Exception as e:
            logger.error(f"حدث خطأ عام أثناء الوصول إلى قاعدة البيانات: {e}")
            return False

# دالة لإعادة تشغيل التطبيق
def restart_app():
    """إعادة تشغيل التطبيق"""
    logger.info("إعادة تشغيل التطبيق")
    
    try:
        # إيقاف العمليات الحالية
        os.system("pkill -f 'gunicorn'")
        os.system("pkill -f 'python main.py'")
        
        # انتظار التوقف
        time.sleep(2)
        
        # إعادة تشغيل التطبيق
        os.system("gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app &")
        
        logger.info("تمت إعادة تشغيل التطبيق بنجاح")
        return True
    
    except Exception as e:
        logger.error(f"حدث خطأ أثناء إعادة تشغيل التطبيق: {e}")
        return False

def main():
    """الدالة الرئيسية"""
    logger.info("بدء عملية إصلاح البوت")
    
    # إضافة دالة get_or_create
    add_get_or_create_method()
    
    # إصلاح نموذج المجموعة
    fix_group_model()
    
    # إصلاح قاعدة البيانات
    fix_database()
    
    # إعادة تشغيل التطبيق
    restart_app()
    
    logger.info("اكتملت عملية إصلاح البوت")

if __name__ == "__main__":
    main()