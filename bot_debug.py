#!/usr/bin/env python3
"""
ملف تصحيح أخطاء البوت وتسجيل الأحداث
يقوم بتتبع جميع الرسائل والتحديثات ويسجلها في ملف لتسهيل اكتشاف الأخطاء
"""

import os
import json
import logging
from datetime import datetime
import traceback
import requests
from flask import Flask, request, jsonify
from study_bot.config import TELEGRAM_API_URL, TELEGRAM_BOT_TOKEN, logger
from study_bot.bot import process_update

# إعداد ملف السجل
LOG_FILE = 'bot_events.log'
DEBUG_LOG_FILE = 'bot_debug.log'

# إعداد التسجيل المفصل
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(DEBUG_LOG_FILE),
        logging.StreamHandler()
    ]
)

debug_logger = logging.getLogger('bot_debug')

def setup_webhook():
    """إعداد ويب هوك تليجرام للبوت"""
    webhook_url = os.environ.get('WEBHOOK_URL')
    if not webhook_url:
        debug_logger.warning("لم يتم تعيين عنوان WEBHOOK_URL")
        return False
    
    url = f"{TELEGRAM_API_URL}/setWebhook"
    payload = {
        'url': webhook_url
    }
    
    try:
        response = requests.post(url, json=payload)
        result = response.json()
        
        if response.status_code == 200 and result.get('ok'):
            debug_logger.info(f"تم إعداد ويب هوك بنجاح: {webhook_url}")
            return True
        else:
            debug_logger.error(f"فشل إعداد ويب هوك: {result}")
            return False
    except Exception as e:
        debug_logger.error(f"استثناء أثناء إعداد ويب هوك: {e}")
        return False

def log_update(update_data):
    """تسجيل التحديث القادم من تليجرام"""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # تحديد نوع التحديث
        update_type = "unknown"
        user_info = {}
        
        if 'message' in update_data:
            message = update_data['message']
            update_type = 'message'
            if 'from' in message:
                user_info = {
                    'user_id': message['from'].get('id'),
                    'username': message['from'].get('username'),
                    'first_name': message['from'].get('first_name'),
                    'last_name': message['from'].get('last_name')
                }
            
            # تسجيل محتوى الرسالة
            content = ""
            if 'text' in message:
                content = f"نص: {message['text']}"
            elif 'photo' in message:
                content = "صورة"
            elif 'document' in message:
                content = f"مستند: {message['document'].get('file_name', 'بدون اسم')}"
            else:
                content = "محتوى غير نصي"
            
            # تسجيل معلومات الدردشة
            chat_info = {
                'chat_id': message.get('chat', {}).get('id'),
                'chat_type': message.get('chat', {}).get('type'),
                'chat_title': message.get('chat', {}).get('title')
            }
            
            log_entry = {
                'timestamp': timestamp,
                'update_type': update_type,
                'user_info': user_info,
                'chat_info': chat_info,
                'content': content,
                'update_data': update_data
            }
            
        elif 'callback_query' in update_data:
            callback = update_data['callback_query']
            update_type = 'callback_query'
            
            if 'from' in callback:
                user_info = {
                    'user_id': callback['from'].get('id'),
                    'username': callback['from'].get('username'),
                    'first_name': callback['from'].get('first_name'),
                    'last_name': callback['from'].get('last_name')
                }
            
            # تسجيل محتوى الاستجابة التفاعلية
            content = f"callback_data: {callback.get('data', 'غير محدد')}"
            
            # تسجيل معلومات الدردشة من الرسالة الأصلية
            chat_info = {
                'chat_id': callback.get('message', {}).get('chat', {}).get('id'),
                'chat_type': callback.get('message', {}).get('chat', {}).get('type'),
                'chat_title': callback.get('message', {}).get('chat', {}).get('title')
            }
            
            log_entry = {
                'timestamp': timestamp,
                'update_type': update_type,
                'user_info': user_info,
                'chat_info': chat_info,
                'content': content,
                'update_data': update_data
            }
            
        else:
            # تسجيل تحديثات أخرى
            log_entry = {
                'timestamp': timestamp,
                'update_type': 'unknown',
                'update_data': update_data
            }
        
        # تحويل القاموس إلى نص JSON
        log_json = json.dumps(log_entry, ensure_ascii=False, indent=2)
        
        # كتابة السجل إلى الملف
        with open(LOG_FILE, 'a', encoding='utf-8') as log_file:
            log_file.write(f"\n--- تحديث جديد ({timestamp}) ---\n")
            log_file.write(log_json)
            log_file.write("\n")
        
        debug_logger.info(f"تم تسجيل تحديث جديد: {update_type}")
        
        return log_entry
    except Exception as e:
        debug_logger.error(f"خطأ في تسجيل التحديث: {e}")
        debug_logger.error(traceback.format_exc())
        return None

def test_bot_connection():
    """اختبار الاتصال ببوت تليجرام"""
    url = f"{TELEGRAM_API_URL}/getMe"
    
    try:
        response = requests.get(url)
        result = response.json()
        
        if response.status_code == 200 and result.get('ok'):
            bot_info = result.get('result', {})
            debug_logger.info(f"تم الاتصال بالبوت بنجاح: {bot_info.get('first_name')} (@{bot_info.get('username')})")
            return True, bot_info
        else:
            debug_logger.error(f"فشل الاتصال بالبوت: {result}")
            return False, result
    except Exception as e:
        debug_logger.error(f"استثناء أثناء الاتصال بالبوت: {e}")
        return False, str(e)

def check_database_tables():
    """التحقق من جداول قاعدة البيانات"""
    try:
        from study_bot.models import db
        
        # الحصول على أسماء الجداول
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        
        debug_logger.info(f"تم العثور على {len(tables)} جدول في قاعدة البيانات")
        
        # فحص أعمدة بعض الجداول الرئيسية
        problematic_tables = []
        
        for table_name in tables:
            columns = inspector.get_columns(table_name)
            column_names = [col['name'] for col in columns]
            debug_logger.info(f"جدول {table_name} يحتوي على {len(columns)} عمود: {', '.join(column_names)}")
            
            # تحقق من وجود مشاكل في جدول GroupScheduleTracker
            if table_name == 'group_schedule_tracker':
                required_columns = ['is_active', 'join_message_id', 'join_deadline']
                missing_columns = [col for col in required_columns if col not in column_names]
                
                if missing_columns:
                    problematic_tables.append({
                        'table': table_name,
                        'missing_columns': missing_columns
                    })
        
        if problematic_tables:
            debug_logger.warning(f"وجدت مشاكل في {len(problematic_tables)} جدول:")
            for table_info in problematic_tables:
                debug_logger.warning(f"جدول {table_info['table']} يفتقد إلى الأعمدة: {', '.join(table_info['missing_columns'])}")
        
        return tables, problematic_tables
    except Exception as e:
        debug_logger.error(f"خطأ أثناء فحص جداول قاعدة البيانات: {e}")
        debug_logger.error(traceback.format_exc())
        return [], []

def send_test_message(chat_id):
    """إرسال رسالة اختبارية إلى دردشة محددة"""
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': "🔄 هذه رسالة اختبارية للتحقق من عمل البوت.\n\nإذا وصلتك هذه الرسالة، فهذا يعني أن البوت يعمل بشكل صحيح!",
        'parse_mode': 'HTML'
    }
    
    try:
        response = requests.post(url, json=payload)
        result = response.json()
        
        if response.status_code == 200 and result.get('ok'):
            debug_logger.info(f"تم إرسال رسالة اختبارية بنجاح إلى {chat_id}")
            return True, result.get('result')
        else:
            debug_logger.error(f"فشل إرسال رسالة اختبارية: {result}")
            return False, result
    except Exception as e:
        debug_logger.error(f"استثناء أثناء إرسال رسالة اختبارية: {e}")
        return False, str(e)

def manually_process_update(update_data):
    """معالجة تحديث تليجرام يدوياً مع تسجيل الأخطاء"""
    try:
        # تسجيل التحديث أولاً
        log_update(update_data)
        
        # محاولة معالجة التحديث
        result = process_update(update_data)
        
        debug_logger.info(f"تمت معالجة التحديث بنجاح: {result}")
        return True, result
    except Exception as e:
        error_msg = f"خطأ في معالجة التحديث: {e}"
        debug_logger.error(error_msg)
        debug_logger.error(traceback.format_exc())
        return False, error_msg

def run_diagnostics():
    """تشغيل تشخيص شامل للبوت"""
    debug_logger.info("=== بدء التشخيص الشامل للبوت ===")
    
    results = {
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'tests': []
    }
    
    # اختبار 1: التحقق من الاتصال بالبوت
    debug_logger.info("1. اختبار الاتصال بالبوت...")
    success, bot_info = test_bot_connection()
    results['tests'].append({
        'name': 'اختبار الاتصال بالبوت',
        'success': success,
        'details': bot_info
    })
    
    # اختبار 2: فحص جداول قاعدة البيانات
    debug_logger.info("2. فحص جداول قاعدة البيانات...")
    tables, problematic_tables = check_database_tables()
    results['tests'].append({
        'name': 'فحص قاعدة البيانات',
        'success': len(problematic_tables) == 0,
        'details': {
            'total_tables': len(tables),
            'problematic_tables': problematic_tables
        }
    })
    
    # اختبار 3: إعداد ويب هوك
    debug_logger.info("3. إعداد ويب هوك...")
    webhook_success = setup_webhook()
    results['tests'].append({
        'name': 'إعداد ويب هوك',
        'success': webhook_success,
        'details': {}
    })
    
    # حفظ نتائج التشخيص
    with open('bot_diagnostics.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    debug_logger.info("=== انتهاء التشخيص الشامل للبوت ===")
    return results

if __name__ == "__main__":
    debug_logger.info("بدء تشغيل أداة تصحيح أخطاء البوت")
    
    # تشغيل التشخيص
    diagnostics_results = run_diagnostics()
    
    # طباعة ملخص النتائج
    print("\n=== ملخص نتائج التشخيص ===")
    for test in diagnostics_results['tests']:
        status = "✅ نجاح" if test['success'] else "❌ فشل"
        print(f"{status} - {test['name']}")
    
    print("\nاكتمل التشخيص. للمزيد من التفاصيل، راجع ملف bot_debug.log")