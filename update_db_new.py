"""
سكريبت لتحديث مخطط قاعدة البيانات
"""

from datetime import datetime
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text, inspect, exc

# تكوين Flask وSQLAlchemy
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


def update_group_table():
    """تحديث جدول المجموعة بإضافة أعمدة جديدة"""
    with app.app_context():
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('group')]
        conn = db.engine.connect()
        
        try:
            transaction = conn.begin()
            
            # إضافة الأعمدة الجديدة
            if 'admin_id' not in columns:
                conn.execute(text("ALTER TABLE \"group\" ADD COLUMN admin_id INTEGER;"))
                print("تمت إضافة العمود admin_id إلى جدول المجموعة")
            
            if 'admin_username' not in columns:
                conn.execute(text("ALTER TABLE \"group\" ADD COLUMN admin_username VARCHAR(100);"))
                print("تمت إضافة العمود admin_username إلى جدول المجموعة")
                
            if 'send_motivational' not in columns:
                conn.execute(text("ALTER TABLE \"group\" ADD COLUMN send_motivational BOOLEAN DEFAULT TRUE;"))
                print("تمت إضافة العمود send_motivational إلى جدول المجموعة")
                
            if 'send_reports' not in columns:
                conn.execute(text("ALTER TABLE \"group\" ADD COLUMN send_reports BOOLEAN DEFAULT TRUE;"))
                print("تمت إضافة العمود send_reports إلى جدول المجموعة")
                
            if 'allow_custom_tasks' not in columns:
                conn.execute(text("ALTER TABLE \"group\" ADD COLUMN allow_custom_tasks BOOLEAN DEFAULT TRUE;"))
                print("تمت إضافة العمود allow_custom_tasks إلى جدول المجموعة")
            
            if 'timezone_offset' not in columns:
                conn.execute(text("ALTER TABLE \"group\" ADD COLUMN timezone_offset INTEGER DEFAULT 3;"))
                print("تمت إضافة العمود timezone_offset إلى جدول المجموعة")
                
            if 'language_code' not in columns:
                conn.execute(text("ALTER TABLE \"group\" ADD COLUMN language_code VARCHAR(10) DEFAULT 'ar';"))
                print("تمت إضافة العمود language_code إلى جدول المجموعة")
            
            if 'morning_schedule_enabled' not in columns:
                conn.execute(text("ALTER TABLE \"group\" ADD COLUMN morning_schedule_enabled BOOLEAN DEFAULT FALSE;"))
                print("تمت إضافة العمود morning_schedule_enabled إلى جدول المجموعة")
            
            if 'evening_schedule_enabled' not in columns:
                conn.execute(text("ALTER TABLE \"group\" ADD COLUMN evening_schedule_enabled BOOLEAN DEFAULT FALSE;"))
                print("تمت إضافة العمود evening_schedule_enabled إلى جدول المجموعة")
            
            if 'custom_schedule_enabled' not in columns:
                conn.execute(text("ALTER TABLE \"group\" ADD COLUMN custom_schedule_enabled BOOLEAN DEFAULT FALSE;"))
                print("تمت إضافة العمود custom_schedule_enabled إلى جدول المجموعة")
            
            if 'motivation_enabled' not in columns:
                conn.execute(text("ALTER TABLE \"group\" ADD COLUMN motivation_enabled BOOLEAN DEFAULT TRUE;"))
                print("تمت إضافة العمود motivation_enabled إلى جدول المجموعة")
                
            transaction.commit()
            print("تم تحديث جدول المجموعة بنجاح")
            
        except Exception as e:
            if 'transaction' in locals() and transaction:
                transaction.rollback()
            print(f"حدث خطأ أثناء تحديث جدول المجموعة: {e}")
        finally:
            conn.close()


def add_user_get_or_create_method():
    """إضافة دالة get_or_create لنموذج المستخدم"""
    print("إضافة دالة get_or_create لنموذج المستخدم")
    with open('study_bot/models/user.py', 'r', encoding='utf-8') as file:
        content = file.read()
    
    if 'def get_or_create(cls, telegram_id, username=None, first_name=None, last_name=None):' not in content:
        # تعيين موقع إضافة الدالة - قبل دالة __repr__
        insert_position = content.find('def __repr__(self):')
        
        if insert_position > 0:
            # البحث عن الكلاس المستهدف
            user_class_position = content.find('class User(UserMixin, db.Model):')
            
            if user_class_position > 0:
                # تحديد مستوى التابع (عدد المسافات البادئة)
                indentation = '    '
                
                # نص الدالة المراد إضافتها
                get_or_create_method = f'''
{indentation}@classmethod
{indentation}def get_or_create(cls, telegram_id, username=None, first_name=None, last_name=None):
{indentation}    """الحصول على المستخدم أو إنشاؤه إذا لم يكن موجودًا"""
{indentation}    from study_bot.models import db
{indentation}    
{indentation}    user = cls.query.filter_by(telegram_id=telegram_id).first()
{indentation}    
{indentation}    if not user:
{indentation}        user = cls(
{indentation}            telegram_id=telegram_id,
{indentation}            username=username,
{indentation}            first_name=first_name,
{indentation}            last_name=last_name
{indentation}        )
{indentation}        db.session.add(user)
{indentation}        try:
{indentation}            db.session.commit()
{indentation}        except Exception as e:
{indentation}            db.session.rollback()
{indentation}            print(f"خطأ في إضافة المستخدم: {e}")
{indentation}            raise
{indentation}    
{indentation}    return user
'''
                
                # تقسيم المحتوى وإضافة الدالة
                before_repr = content[:insert_position]
                after_repr = content[insert_position:]
                
                new_content = before_repr + get_or_create_method + after_repr
                
                with open('study_bot/models/user.py', 'w', encoding='utf-8') as file:
                    file.write(new_content)
                
                print("تمت إضافة دالة get_or_create لنموذج المستخدم بنجاح")
            else:
                print("لم يتم العثور على كلاس المستخدم في الملف")
        else:
            print("لم يتم العثور على دالة __repr__ لتحديد موقع الإضافة")
    else:
        print("دالة get_or_create موجودة بالفعل")


def update_group_participant_table():
    """تحديث جدول مشاركي المجموعة بإضافة أعمدة جديدة"""
    with app.app_context():
        inspector = inspect(db.engine)
        
        if not inspect_table_exists('group_task_participant'):
            print("جدول group_task_participant غير موجود")
            return
            
        columns = [col['name'] for col in inspector.get_columns('group_task_participant')]
        conn = db.engine.connect()
        
        try:
            transaction = conn.begin()
            
            # إضافة الأعمدة الجديدة
            if 'daily_completion_count' not in columns:
                conn.execute(text("ALTER TABLE group_task_participant ADD COLUMN daily_completion_count INTEGER DEFAULT 0;"))
                print("تمت إضافة العمود daily_completion_count إلى جدول مشاركي المجموعة")
                
            if 'total_completion_count' not in columns:
                conn.execute(text("ALTER TABLE group_task_participant ADD COLUMN total_completion_count INTEGER DEFAULT 0;"))
                print("تمت إضافة العمود total_completion_count إلى جدول مشاركي المجموعة")
            
            transaction.commit()
            print("تم تحديث جدول مشاركي المجموعة بنجاح")
            
        except Exception as e:
            if 'transaction' in locals() and transaction:
                transaction.rollback()
            print(f"حدث خطأ أثناء تحديث جدول مشاركي المجموعة: {e}")
        finally:
            conn.close()


def create_new_task_tables():
    """إنشاء جداول المهام الجديدة"""
    with app.app_context():
        inspector = inspect(db.engine)
        conn = db.engine.connect()
        
        try:
            transaction = conn.begin()
            
            # إنشاء جدول متابعة جدول المجموعة إذا لم يكن موجودًا
            if not inspect_table_exists('group_schedule_tracker'):
                conn.execute(text("""
                CREATE TABLE group_schedule_tracker (
                    id SERIAL PRIMARY KEY,
                    group_id INTEGER NOT NULL REFERENCES "group" (id),
                    schedule_type VARCHAR(20) NOT NULL DEFAULT 'morning',
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    start_date TIMESTAMP WITH TIME ZONE,
                    end_date TIMESTAMP WITH TIME ZONE,
                    settings TEXT
                );
                """))
                print("تم إنشاء جدول group_schedule_tracker")
            
            # إنشاء جدول متابعة مهام المجموعة إذا لم يكن موجودًا
            if not inspect_table_exists('group_task_tracker'):
                conn.execute(text("""
                CREATE TABLE group_task_tracker (
                    id SERIAL PRIMARY KEY,
                    group_id INTEGER NOT NULL REFERENCES "group" (id),
                    task_type VARCHAR(50) NOT NULL,
                    scheduled_time TIMESTAMP WITH TIME ZONE NOT NULL,
                    deadline_minutes INTEGER DEFAULT 10,
                    is_sent BOOLEAN DEFAULT FALSE,
                    sent_at TIMESTAMP WITH TIME ZONE,
                    message TEXT,
                    message_id INTEGER,
                    join_button_text VARCHAR(100)
                );
                """))
                print("تم إنشاء جدول group_task_tracker")
            
            # إنشاء جدول مشارك مهام المجموعة إذا لم يكن موجودًا
            if not inspect_table_exists('group_task_participant'):
                conn.execute(text("""
                CREATE TABLE group_task_participant (
                    id SERIAL PRIMARY KEY,
                    group_id INTEGER NOT NULL REFERENCES "group" (id),
                    user_id INTEGER NOT NULL REFERENCES "user" (id),
                    schedule_type VARCHAR(20) NOT NULL DEFAULT 'morning',
                    join_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    last_completion_date TIMESTAMP WITH TIME ZONE,
                    daily_completion_count INTEGER DEFAULT 0,
                    total_completion_count INTEGER DEFAULT 0
                );
                """))
                print("تم إنشاء جدول group_task_participant")
            
            # إنشاء جدول مشاركة مهمة مجموعة إذا لم يكن موجودًا
            if not inspect_table_exists('group_task_participation'):
                conn.execute(text("""
                CREATE TABLE group_task_participation (
                    id SERIAL PRIMARY KEY,
                    task_id INTEGER NOT NULL REFERENCES group_task_tracker (id),
                    participant_id INTEGER NOT NULL REFERENCES group_task_participant (id),
                    completion_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                """))
                print("تم إنشاء جدول group_task_participation")
            
            # إنشاء جدول الرسائل التحفيزية إذا لم يكن موجودًا
            if not inspect_table_exists('motivational_message'):
                conn.execute(text("""
                CREATE TABLE motivational_message (
                    id SERIAL PRIMARY KEY,
                    group_id INTEGER NOT NULL REFERENCES "group" (id),
                    message TEXT NOT NULL,
                    sent_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    message_id INTEGER
                );
                """))
                print("تم إنشاء جدول motivational_message")
            
            transaction.commit()
            print("تم إنشاء جداول المهام الجديدة بنجاح")
            
        except Exception as e:
            if 'transaction' in locals() and transaction:
                transaction.rollback()
            print(f"حدث خطأ أثناء إنشاء جداول المهام الجديدة: {e}")
        finally:
            conn.close()


def update_group_schedule_tracker_table():
    """تحديث جدول تتبع جداول المجموعة بإضافة الأعمدة المفقودة"""
    with app.app_context():
        inspector = inspect(db.engine)
        
        if not inspect_table_exists('group_schedule_tracker'):
            print("جدول group_schedule_tracker غير موجود")
            return
            
        columns = [col['name'] for col in inspector.get_columns('group_schedule_tracker')]
        conn = db.engine.connect()
        
        try:
            transaction = conn.begin()
            
            # إضافة الأعمدة المفقودة
            if 'settings' not in columns:
                conn.execute(text("ALTER TABLE group_schedule_tracker ADD COLUMN settings TEXT;"))
                print("تمت إضافة العمود settings إلى جدول group_schedule_tracker")
            
            transaction.commit()
            print("تم تحديث جدول تتبع جداول المجموعة بنجاح")
            
        except Exception as e:
            if 'transaction' in locals() and transaction:
                transaction.rollback()
            print(f"حدث خطأ أثناء تحديث جدول تتبع جداول المجموعة: {e}")
        finally:
            conn.close()


def inspect_table_exists(table_name):
    """التحقق من وجود جدول"""
    inspector = inspect(db.engine)
    return table_name in inspector.get_table_names()


if __name__ == "__main__":
    print("بدء تحديث قاعدة البيانات...")
    update_group_table()
    add_user_get_or_create_method()
    update_group_participant_table()
    create_new_task_tables()
    update_group_schedule_tracker_table()
    print("اكتمل تحديث قاعدة البيانات")