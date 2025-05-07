#!/usr/bin/env python3
"""
Script to fix bot issues
"""

import os
import sys
import time
from flask import Flask
from sqlalchemy import text, inspect, Column, String, Boolean
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('bot_fixer')

# Create Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Function to add get_or_create method to User model
def add_get_or_create_method():
    """Add get_or_create method to User model"""
    logger.info("Adding get_or_create method to User model")
    
    try:
        user_model_path = 'study_bot/models/user.py'
        with open(user_model_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Check if method already exists
        if '@classmethod\n    def get_or_create(' in content:
            logger.info("get_or_create method already exists")
            return True
        
        # Find insertion point - before __repr__ method
        repr_position = content.find('def __repr__(self):')
        if repr_position > 0:
            # Prepare method text with proper docstring format
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
                logger.error(f"Error adding user: {e}")
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
            return True
        else:
            logger.error("Could not find suitable location to add method")
            return False
    
    except Exception as e:
        logger.error(f"Error adding get_or_create method: {e}")
        return False

# Function to fix username column issue in Group model
def fix_group_model():
    """Fix username column issue in Group model"""
    logger.info("Fixing username column issue in Group model")
    
    try:
        group_model_path = 'study_bot/models/group.py'
        with open(group_model_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Check if username column exists
        username_column_exists = 'username = Column(String' in content
        
        if username_column_exists:
            logger.info("username column already exists in Group model")
        else:
            # Add username column after telegram_id
            telegram_id_position = content.find('telegram_id = Column(Integer')
            if telegram_id_position > 0:
                # Find end of line
                line_end = content.find('\n', telegram_id_position)
                
                # Create username column definition
                username_column = '\n    username = Column(String(100), nullable=True)'
                
                # Add column after telegram_id
                new_content = content[:line_end] + username_column + content[line_end:]
                
                # Save modified file
                with open(group_model_path, 'w', encoding='utf-8') as file:
                    file.write(new_content)
                
                logger.info("Added username column to Group model")
            else:
                logger.error("Could not find telegram_id column in Group model")
        
        return True
    
    except Exception as e:
        logger.error(f"Error fixing Group model: {e}")
        return False

# Function to fix database schema
def fix_database():
    """Fix database schema"""
    logger.info("Fixing database schema")
    
    from flask_sqlalchemy import SQLAlchemy
    db = SQLAlchemy(app)
    
    with app.app_context():
        try:
            # Check if columns exist
            inspector = inspect(db.engine)
            group_columns = [col['name'] for col in inspector.get_columns('group')]
            
            # Open connection to execute SQL queries
            conn = db.engine.connect()
            transaction = conn.begin()
            
            try:
                # Add username column if it doesn't exist
                if 'username' not in group_columns:
                    conn.execute(text('ALTER TABLE "group" ADD COLUMN username VARCHAR(100);'))
                    logger.info("Added username column to group table")
                
                # Add required columns to table
                if 'morning_schedule_enabled' not in group_columns:
                    conn.execute(text('ALTER TABLE "group" ADD COLUMN morning_schedule_enabled BOOLEAN DEFAULT FALSE;'))
                    logger.info("Added morning_schedule_enabled column to group table")
                
                if 'evening_schedule_enabled' not in group_columns:
                    conn.execute(text('ALTER TABLE "group" ADD COLUMN evening_schedule_enabled BOOLEAN DEFAULT FALSE;'))
                    logger.info("Added evening_schedule_enabled column to group table")
                
                if 'custom_schedule_enabled' not in group_columns:
                    conn.execute(text('ALTER TABLE "group" ADD COLUMN custom_schedule_enabled BOOLEAN DEFAULT FALSE;'))
                    logger.info("Added custom_schedule_enabled column to group table")
                
                if 'motivation_enabled' not in group_columns:
                    conn.execute(text('ALTER TABLE "group" ADD COLUMN motivation_enabled BOOLEAN DEFAULT TRUE;'))
                    logger.info("Added motivation_enabled column to group table")
                
                # Save changes
                transaction.commit()
                logger.info("Successfully saved changes to database")
                return True
            
            except Exception as e:
                transaction.rollback()
                logger.error(f"Error updating database: {e}")
                return False
            
            finally:
                conn.close()
        
        except Exception as e:
            logger.error(f"General error accessing database: {e}")
            return False

# Function to restart application
def restart_app():
    """Restart application"""
    logger.info("Restarting application")
    
    try:
        # Stop current processes
        os.system("pkill -f 'gunicorn'")
        os.system("pkill -f 'python main.py'")
        
        # Wait for shutdown
        time.sleep(2)
        
        # Restart application
        os.system("gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app &")
        
        logger.info("Successfully restarted application")
        return True
    
    except Exception as e:
        logger.error(f"Error restarting application: {e}")
        return False

def main():
    """Main function"""
    logger.info("Starting bot fix process")
    
    # Add get_or_create method
    add_get_or_create_method()
    
    # Fix Group model
    fix_group_model()
    
    # Fix database
    fix_database()
    
    # Restart application
    restart_app()
    
    logger.info("Bot fix process completed")

if __name__ == "__main__":
    main()