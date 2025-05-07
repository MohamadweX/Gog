"""
أدوات الرسائل للبوت
تحتوي على وظائف للتفاعل مع واجهة برمجة تطبيقات تيليجرام
"""

import json
import requests
import logging
from datetime import datetime
import random
import os

# إعداد التسجيل إذا لم يكن موجودًا
logger = logging.getLogger('study_bot')

# الحصول على رمز الوصول لتيليجرام بوت
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

def send_message(chat_id, text, reply_markup=None, parse_mode=None, reply_to_message_id=None):
    """إرسال رسالة إلى مستخدم أو مجموعة"""
    payload = {
        'chat_id': chat_id,
        'text': text
    }
    
    if reply_markup:
        payload['reply_markup'] = json.dumps(reply_markup)
    
    if parse_mode:
        payload['parse_mode'] = parse_mode
    
    if reply_to_message_id:
        payload['reply_to_message_id'] = reply_to_message_id
    
    try:
        response = requests.post(f"{API_URL}/sendMessage", json=payload)
        data = response.json()
        
        if data.get('ok'):
            return data.get('result')
        else:
            logger.error(f"خطأ في إرسال الرسالة: {data.get('description')}")
            return None
    except Exception as e:
        logger.error(f"خطأ في إرسال الرسالة: {e}")
        return None

def edit_message(chat_id, message_id, text, reply_markup=None, parse_mode=None):
    """تعديل رسالة موجودة"""
    payload = {
        'chat_id': chat_id,
        'message_id': message_id,
        'text': text
    }
    
    if reply_markup:
        payload['reply_markup'] = json.dumps(reply_markup)
    
    if parse_mode:
        payload['parse_mode'] = parse_mode
    
    try:
        response = requests.post(f"{API_URL}/editMessageText", json=payload)
        data = response.json()
        
        if data.get('ok'):
            return data.get('result')
        else:
            logger.error(f"خطأ في تعديل الرسالة: {data.get('description')}")
            return None
    except Exception as e:
        logger.error(f"خطأ في تعديل الرسالة: {e}")
        return None

def delete_message(chat_id, message_id):
    """حذف رسالة"""
    payload = {
        'chat_id': chat_id,
        'message_id': message_id
    }
    
    try:
        response = requests.post(f"{API_URL}/deleteMessage", json=payload)
        data = response.json()
        
        if data.get('ok'):
            return True
        else:
            logger.error(f"خطأ في حذف الرسالة: {data.get('description')}")
            return False
    except Exception as e:
        logger.error(f"خطأ في حذف الرسالة: {e}")
        return False

def answer_callback_query(callback_query_id, text=None, show_alert=False):
    """الإجابة على استعلام callback"""
    payload = {
        'callback_query_id': callback_query_id
    }
    
    if text:
        payload['text'] = text
    
    if show_alert:
        payload['show_alert'] = show_alert
    
    try:
        response = requests.post(f"{API_URL}/answerCallbackQuery", json=payload)
        data = response.json()
        
        if data.get('ok'):
            return True
        else:
            logger.error(f"خطأ في الإجابة على استعلام الاستجابة: {data.get('description')}")
            return False
    except Exception as e:
        logger.error(f"خطأ في الإجابة على استعلام الاستجابة: {e}")
        return False