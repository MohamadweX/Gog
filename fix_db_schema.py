#!/usr/bin/env python3
"""
Script to fix database schema to match models
"""

import os
import logging
from flask import Flask
from sqlalchemy import text, inspect

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('db_fixer')

# Create Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

def fix_group_table():
    """Fix group table schema"""
    from flask_sqlalchemy import SQLAlchemy
    db = SQLAlchemy(app)
    
    with app.app_context():
        try:
            # Check if columns exist
            inspector = inspect(db.engine)
            group_columns = [col['name'] for col in inspector.get_columns('group')]
            
            # Define all columns that should exist in the Group model
            required_columns = {
                # Basic columns
                'id': 'INTEGER', 
                'telegram_id': 'INTEGER',
                'title': 'VARCHAR(255)',
                'username': 'VARCHAR(100)',
                'description': 'TEXT',
                'is_active': 'BOOLEAN',
                'is_private': 'BOOLEAN',
                'is_authenticated': 'BOOLEAN',
                'creation_date': 'TIMESTAMP WITH TIME ZONE',
                'admin_id': 'INTEGER',
                'admin_username': 'VARCHAR(100)',
                
                # Settings
                'send_motivational': 'BOOLEAN',
                'send_reports': 'BOOLEAN',
                'allow_custom_tasks': 'BOOLEAN',
                'timezone_offset': 'INTEGER',
                'language_code': 'VARCHAR(10)',
                
                # Schedule settings
                'morning_schedule_enabled': 'BOOLEAN',
                'evening_schedule_enabled': 'BOOLEAN',
                'custom_schedule_enabled': 'BOOLEAN',
                'motivation_enabled': 'BOOLEAN',
                
                # Stats
                'total_messages': 'INTEGER',
                'total_tasks': 'INTEGER',
                'total_participants': 'INTEGER',
                'total_completions': 'INTEGER'
            }
            
            # Open connection to execute SQL queries
            conn = db.engine.connect()
            transaction = conn.begin()
            
            try:
                # Add missing columns
                for column_name, column_type in required_columns.items():
                    if column_name not in group_columns:
                        # Determine default value based on column type
                        default_value = "DEFAULT FALSE" if "BOOLEAN" in column_type else ""
                        if "INTEGER" in column_type:
                            default_value = "DEFAULT 0"
                        elif "VARCHAR" in column_type or "TEXT" in column_type:
                            default_value = ""
                        
                        # Add the column
                        sql = f'ALTER TABLE "group" ADD COLUMN {column_name} {column_type} {default_value};'
                        conn.execute(text(sql))
                        logger.info(f"Added column {column_name} ({column_type}) to group table")
                
                # Save changes
                transaction.commit()
                logger.info("Successfully updated group table schema")
                return True
            
            except Exception as e:
                transaction.rollback()
                logger.error(f"Error updating group table: {e}")
                return False
            
            finally:
                conn.close()
        
        except Exception as e:
            logger.error(f"General error accessing database: {e}")
            return False

def update_user_model():
    """Add get_or_create method to User model if missing"""
    try:
        user_model_path = 'study_bot/models/user.py'
        with open(user_model_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Check if method already exists
        if 'def get_or_create(' in content:
            logger.info("get_or_create method already exists in User model")
            return True
        
        # Find insertion point - before __repr__ method
        repr_position = content.find('def __repr__(self):')
        if repr_position > 0:
            # Prepare method text
            get_or_create_method = """
    @classmethod
    def get_or_create(cls, telegram_id, username=None, first_name=None, last_name=None):
        # Get user or create if not exists
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
                print(f"Error adding user: {e}")
                raise
        
        return user
        
"""
            
            # Split content and add method
            before_repr = content[:repr_position]
            after_repr = content[repr_position:]
            
            new_content = before_repr + get_or_create_method + after_repr
            
            # Save modified file
            with open(user_model_path, 'w', encoding='utf-8') as file:
                file.write(new_content)
            
            logger.info("Successfully added get_or_create method to User model")
        else:
            logger.warning("Could not find suitable location to add get_or_create method")
        
        return True
    
    except Exception as e:
        logger.error(f"Error updating User model: {e}")
        return False

def restart_application():
    """Restart the application to apply changes"""
    import os
    import time
    
    try:
        # First stop any gunicorn processes
        os.system("pkill -f gunicorn")
        
        # Wait a bit
        time.sleep(2)
        
        # Start gunicorn again
        os.system("gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app &")
        
        logger.info("Application restarted successfully")
        return True
    
    except Exception as e:
        logger.error(f"Error restarting application: {e}")
        return False

def main():
    """Main function"""
    logger.info("Starting database fix process")
    
    # Fix group table
    fix_group_table()
    
    # Update user model
    update_user_model()
    
    # Restart application
    restart_application()
    
    logger.info("Database fix process completed")

if __name__ == "__main__":
    main()