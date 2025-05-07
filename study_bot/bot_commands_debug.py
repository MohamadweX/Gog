#!/usr/bin/env python3
"""
وحدة تصحيح أخطاء أوامر البوت
تستخدم لتسجيل جميع الأوامر وتفاعلات المستخدمين في ملف سجل مخصص
مع إضافة إمكانية تتبع الأخطاء بشكل تفصيلي
"""

import os
import logging
import json
import traceback
from datetime import datetime

from study_bot.config import logger, TELEGRAM_API_URL, TELEGRAM_BOT_TOKEN, get_current_time

# إنشاء مجلد السجلات إذا لم يكن موجودًا
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

# إعداد مسجل سجلات الأوامر
COMMANDS_LOG_FILE = os.path.join(LOG_DIR, 'commands.log')
commands_logger = logging.getLogger('commands_logger')
commands_logger.setLevel(logging.DEBUG)

# إضافة معالج ملف لمسجل الأوامر
file_handler = logging.FileHandler(COMMANDS_LOG_FILE, encoding='utf-8')
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))
commands_logger.addHandler(file_handler)

# إعداد مسجل سجلات التحديثات من تيليجرام
UPDATES_LOG_FILE = os.path.join(LOG_DIR, 'telegram_updates.log')
updates_logger = logging.getLogger('updates_logger')
updates_logger.setLevel(logging.DEBUG)

# إضافة معالج ملف لمسجل التحديثات
updates_file_handler = logging.FileHandler(UPDATES_LOG_FILE, encoding='utf-8')
updates_file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))
updates_logger.addHandler(updates_file_handler)

# إعداد مسجل سجلات الأخطاء
ERRORS_LOG_FILE = os.path.join(LOG_DIR, 'bot_errors.log')
errors_logger = logging.getLogger('errors_logger')
errors_logger.setLevel(logging.ERROR)

# إضافة معالج ملف لمسجل الأخطاء
errors_file_handler = logging.FileHandler(ERRORS_LOG_FILE, encoding='utf-8')
errors_file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s\n%(stack_trace)s\n',
    datefmt='%Y-%m-%d %H:%M:%S'
))
errors_logger.addHandler(errors_file_handler)


def log_command(user_id, chat_id, command, args=None):
    """تسجيل أمر من المستخدم"""
    message = f"تم استلام أمر: {command} من المستخدم {user_id} في الدردشة {chat_id}"
    if args:
        message += f" مع الوسائط: {args}"
    
    commands_logger.info(message)
    logger.info(message)


def log_update(update_data):
    """تسجيل التحديث القادم من تيليجرام"""
    updates_logger.debug(f"تحديث تيليجرام: {json.dumps(update_data, ensure_ascii=False, indent=2)}")


def log_error(error_type, error_message, stack_trace=None):
    """تسجيل خطأ"""
    if stack_trace is None:
        stack_trace = traceback.format_exc()
    
    errors_logger.error(
        error_message, 
        extra={
            'error_type': error_type,
            'stack_trace': stack_trace
        }
    )
    logger.error(f"خطأ من النوع {error_type}: {error_message}")


def log_callback_query(user_id, chat_id, callback_data):
    """تسجيل استجابة استعلام الرد"""
    message = f"تم استلام استعلام استجابة: {callback_data} من المستخدم {user_id} في الدردشة {chat_id}"
    commands_logger.info(message)
    logger.info(message)


def test_bot_token():
    """اختبار صلاحية توكن البوت مع واجهة برمجة تطبيقات تيليجرام"""
    import requests
    
    try:
        # إضافة توكن البوت إلى عنوان URL
        url = f"{TELEGRAM_API_URL}/bot{TELEGRAM_BOT_TOKEN}/getMe"
        logger.debug(f"محاولة التحقق من توكن البوت باستخدام: {url}")
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok', False):
                bot_info = data.get('result', {})
                logger.info(f"تم التحقق من توكن البوت: {bot_info.get('username')} (ID: {bot_info.get('id')})")
                commands_logger.info(f"توكن البوت صالح: {bot_info.get('username')} (ID: {bot_info.get('id')})")
                return True, bot_info
            else:
                error_msg = data.get('description', 'خطأ غير معروف')
                logger.error(f"توكن البوت غير صالح: {error_msg}")
                commands_logger.error(f"توكن البوت غير صالح: {error_msg}")
                return False, error_msg
        else:
            logger.error(f"فشل طلب التحقق من توكن البوت، رمز الاستجابة: {response.status_code}")
            commands_logger.error(f"فشل طلب التحقق من توكن البوت، رمز الاستجابة: {response.status_code}")
            return False, f"رمز استجابة HTTP: {response.status_code}"
    
    except Exception as e:
        error_message = f"استثناء أثناء التحقق من توكن البوت: {str(e)}"
        logger.error(error_message)
        log_error("bot_token_verification", error_message)
        return False, str(e)


def log_message_processing(update_id, message_data, user_id=None, chat_id=None):
    """تسجيل معالجة الرسالة"""
    message = (
        f"معالجة تحديث {update_id} - "
        f"مستخدم: {user_id or 'غير معروف'}, "
        f"دردشة: {chat_id or 'غير معروفة'}"
    )
    commands_logger.debug(message)
    
    # إذا كانت رسالة عادية
    if 'text' in message_data:
        text = message_data.get('text', '')
        commands_logger.info(f"نص الرسالة: {text}")
        
        # التحقق مما إذا كان الأمر
        if text.startswith('/'):
            command_parts = text.split()
            command = command_parts[0]
            args = command_parts[1:] if len(command_parts) > 1 else None
            log_command(user_id, chat_id, command, args)