#!/usr/bin/env python3
"""
وحدة تسجيل سجلات البوت
تحتوي على وظائف ومعالجات لتسجيل جميع أحداث البوت والأخطاء بشكل تفصيلي
"""

import os
import logging
import time
import traceback
import json
from datetime import datetime
from functools import wraps

from study_bot.config import SCHEDULER_TIMEZONE, get_current_time

# إنشاء مجلد السجلات إذا لم يكن موجودًا
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

# إعداد ملف سجل تفاصيل البوت
BOT_LOG_FILE = os.path.join(LOG_DIR, 'bot_details.log')

# إعداد ملف سجل الأخطاء
ERROR_LOG_FILE = os.path.join(LOG_DIR, 'bot_errors.log')

# إعداد ملف سجل الأوامر
COMMAND_LOG_FILE = os.path.join(LOG_DIR, 'bot_commands.log')

# إعداد ملف سجل تفاعلات المستخدمين
USER_INTERACTION_LOG_FILE = os.path.join(LOG_DIR, 'user_interactions.log')

# إعداد مسجل سجلات تفاصيل البوت
bot_logger = logging.getLogger('bot_details')
bot_logger.setLevel(logging.INFO)
bot_file_handler = logging.FileHandler(BOT_LOG_FILE, encoding='utf-8')
bot_file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s', 
    datefmt='%Y-%m-%d %H:%M:%S'
))
bot_logger.addHandler(bot_file_handler)

# إعداد مسجل سجلات الأخطاء
error_logger = logging.getLogger('bot_errors')
error_logger.setLevel(logging.ERROR)
error_file_handler = logging.FileHandler(ERROR_LOG_FILE, encoding='utf-8')
error_file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s\n%(stack_trace)s\n', 
    datefmt='%Y-%m-%d %H:%M:%S'
))
error_logger.addHandler(error_file_handler)

# إعداد مسجل سجلات الأوامر
command_logger = logging.getLogger('bot_commands')
command_logger.setLevel(logging.INFO)
command_file_handler = logging.FileHandler(COMMAND_LOG_FILE, encoding='utf-8')
command_file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s', 
    datefmt='%Y-%m-%d %H:%M:%S'
))
command_logger.addHandler(command_file_handler)

# إعداد مسجل سجلات تفاعلات المستخدمين
user_logger = logging.getLogger('user_interactions')
user_logger.setLevel(logging.INFO)
user_file_handler = logging.FileHandler(USER_INTERACTION_LOG_FILE, encoding='utf-8')
user_file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s', 
    datefmt='%Y-%m-%d %H:%M:%S'
))
user_logger.addHandler(user_file_handler)


def log_bot_activity(activity_type, details):
    """تسجيل نشاط البوت"""
    message = f"{activity_type}: {json.dumps(details, ensure_ascii=False)}"
    bot_logger.info(message)


def log_error(error_type, error_message, stack_trace=None):
    """تسجيل خطأ في البوت"""
    if stack_trace is None:
        stack_trace = traceback.format_exc()
    
    error_logger.error(
        error_message, 
        extra={
            'error_type': error_type,
            'stack_trace': stack_trace
        }
    )


def log_command(user_id, chat_id, command, args=None):
    """تسجيل أمر مستلم"""
    details = {
        'user_id': user_id,
        'chat_id': chat_id,
        'command': command,
        'args': args,
        'timestamp': get_current_time().strftime('%Y-%m-%d %H:%M:%S')
    }
    message = f"تم استلام أمر: {command} من المستخدم {user_id} في الدردشة {chat_id}"
    command_logger.info(message)
    log_bot_activity('command', details)


def log_user_interaction(user_id, chat_id, interaction_type, details=None):
    """تسجيل تفاعل المستخدم"""
    if details is None:
        details = {}
    
    interaction_data = {
        'user_id': user_id,
        'chat_id': chat_id,
        'interaction_type': interaction_type,
        'details': details,
        'timestamp': get_current_time().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    message = f"تفاعل المستخدم: {interaction_type} من المستخدم {user_id} في الدردشة {chat_id}"
    user_logger.info(message)
    log_bot_activity('interaction', interaction_data)


def log_callback_query(user_id, chat_id, callback_data):
    """تسجيل استجابة استعلام الرد"""
    details = {
        'user_id': user_id,
        'chat_id': chat_id,
        'callback_data': callback_data,
        'timestamp': get_current_time().strftime('%Y-%m-%d %H:%M:%S')
    }
    message = f"تم استلام استجابة استعلام: {callback_data} من المستخدم {user_id} في الدردشة {chat_id}"
    user_logger.info(message)
    log_bot_activity('callback_query', details)


def log_message_delivery(message_type, chat_id, message_id, content_preview=None):
    """تسجيل تسليم رسالة"""
    details = {
        'message_type': message_type,
        'chat_id': chat_id,
        'message_id': message_id,
        'content_preview': content_preview[:100] + '...' if content_preview and len(content_preview) > 100 else content_preview,
        'timestamp': get_current_time().strftime('%Y-%m-%d %H:%M:%S')
    }
    message = f"تم إرسال رسالة من نوع: {message_type} إلى الدردشة {chat_id}"
    bot_logger.info(message)
    log_bot_activity('message_delivery', details)


def timing_decorator(func):
    """مزخرف لقياس وقت تنفيذ الدالة"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            end_time = time.time()
            execution_time = (end_time - start_time) * 1000  # بالميللي ثانية
            
            # تسجيل معلومات التنفيذ فقط إذا استغرق وقتًا طويلاً (أكثر من 500 ميللي ثانية)
            if execution_time > 500:
                log_bot_activity('slow_execution', {
                    'function': func.__name__,
                    'execution_time_ms': execution_time,
                    'timestamp': get_current_time().strftime('%Y-%m-%d %H:%M:%S')
                })
            
            return result
        except Exception as e:
            end_time = time.time()
            execution_time = (end_time - start_time) * 1000
            log_error(
                'function_error',
                f"خطأ في تنفيذ الدالة {func.__name__}: {str(e)}",
                traceback.format_exc()
            )
            # إعادة ارسال الخطأ ليتم معالجته بواسطة مستوى آخر
            raise
    
    return wrapper


def exception_handler(func):
    """مزخرف للتعامل مع الاستثناءات وتسجيلها"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            log_error(
                'exception_in_function',
                f"استثناء غير محصور في الدالة {func.__name__}: {str(e)}",
                traceback.format_exc()
            )
            # إعادة ارسال الخطأ ليتم معالجته بواسطة مستوى آخر
            raise
    
    return wrapper