"""
وحدة البوت الرئيسية
تحتوي على تهيئة البوت وحلقة الأحداث
"""

import os
import json
import threading
import time
import logging
from datetime import datetime
import requests
from flask import Flask, current_app

from study_bot.config import logger, SCHEDULER_TIMEZONE, TELEGRAM_API_URL, TELEGRAM_BOT_TOKEN, get_current_time
from study_bot.models import db, User, MessageLog
from study_bot.bot_commands_debug import log_update, log_error, log_command, log_callback_query, test_bot_token, log_message_processing

# المتغيرات العامة
_bot_thread = None
_bot_running = False
_last_update_id = 0
UPDATE_INTERVAL = 1  # الفترة الزمنية بين طلبات التحديثات (بالثواني)

def init_bot(app):
    """تهيئة البوت"""
    global _bot_thread, _bot_running
    
    if _bot_running or _bot_thread and _bot_thread.is_alive():
        logger.warning("البوت يعمل بالفعل")
        return
    
    # التحقق من توكن البوت قبل البدء
    logger.info("التحقق من توكن البوت...")
    is_valid, bot_info = test_bot_token()
    
    if not is_valid:
        logger.error("فشل التحقق من توكن البوت. يرجى التحقق من صحة التوكن.")
        return None
    
    logger.info(f"تم التحقق من توكن البوت بنجاح: {bot_info.get('username')} (ID: {bot_info.get('id')})")
    
    # بدء تشغيل سلسلة البوت
    _bot_running = True
    _bot_thread = threading.Thread(target=bot_thread_func, args=(app,))
    _bot_thread.daemon = True
    _bot_thread.start()
    
    logger.info("تم بدء تشغيل سلسلة البوت")
    return _bot_thread

def stop_bot():
    """إيقاف البوت"""
    global _bot_running
    
    if not _bot_running:
        logger.warning("البوت ليس قيد التشغيل")
        return False
    
    logger.info("إيقاف البوت")
    _bot_running = False
    time.sleep(UPDATE_INTERVAL + 1)  # انتظار انتهاء الدورة الحالية
    
    logger.info("تم إيقاف البوت")
    return True

def bot_thread_func(app):
    """دالة سلسلة البوت"""
    global _last_update_id, _bot_running
    
    with app.app_context():
        logger.info("بدء حلقة البوت")
        
        try:
            while _bot_running:
                try:
                    # الحصول على التحديثات
                    updates = get_updates()
                    
                    if updates:
                        # معالجة التحديثات
                        process_updates(updates)
                    
                    # انتظار الفترة الزمنية المحددة
                    time.sleep(UPDATE_INTERVAL)
                except Exception as e:
                    logger.error(f"حدث خطأ أثناء حلقة البوت: {e}")
                    time.sleep(UPDATE_INTERVAL * 5)  # انتظار فترة أطول في حالة حدوث خطأ
        except Exception as e:
            logger.error(f"حدث خطأ فادح في سلسلة البوت: {e}")
        finally:
            _bot_running = False
            logger.info("تم إنهاء حلقة البوت")

def get_updates():
    """الحصول على التحديثات من واجهة برمجة تطبيقات تيليجرام"""
    global _last_update_id
    
    try:
        # بناء رابط الطلب مع توكن البوت
        url = f"{TELEGRAM_API_URL}/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
        
        # بناء البيانات
        data = {
            "offset": _last_update_id + 1,
            "timeout": 30
        }
        
        # إرسال الطلب
        response = requests.post(url, json=data, timeout=60)
        
        # التحقق من نجاح الطلب
        if response.status_code != 200:
            logger.error(f"فشل الحصول على التحديثات: {response.text}")
            return []
        
        # تحليل الاستجابة
        result = response.json()
        
        if not result["ok"]:
            logger.error(f"خطأ في الحصول على التحديثات: {result}")
            return []
        
        updates = result["result"]
        
        # تحديث آخر معرف للتحديث
        if updates:
            _last_update_id = updates[-1]["update_id"]
        
        return updates
    except Exception as e:
        logger.error(f"حدث خطأ أثناء الحصول على التحديثات: {e}")
        return []

def process_updates(updates):
    """معالجة التحديثات"""
    for update in updates:
        try:
            # معالجة التحديث بناءً على نوعه
            if "message" in update:
                try:
                    handle_message(update["message"])
                except Exception as e:
                    logger.error(f"خطأ في معالجة رسالة: {e}")
                    # إعادة تعيين الجلسة في حالة حدوث خطأ في قاعدة البيانات
                    try:
                        db.session.rollback()
                    except:
                        pass
            elif "callback_query" in update:
                try:
                    handle_callback_query(update["callback_query"])
                except Exception as e:
                    logger.error(f"خطأ في معالجة استجابة: {e}")
                    # إعادة تعيين الجلسة في حالة حدوث خطأ في قاعدة البيانات
                    try:
                        db.session.rollback()
                    except:
                        pass
            elif "chat_member" in update:
                try:
                    handle_chat_member(update["chat_member"])
                except Exception as e:
                    logger.error(f"خطأ في معالجة عضو دردشة: {e}")
                    # إعادة تعيين الجلسة في حالة حدوث خطأ في قاعدة البيانات
                    try:
                        db.session.rollback()
                    except:
                        pass
        except Exception as e:
            logger.error(f"حدث خطأ عام أثناء معالجة التحديث: {e}")
            # إعادة تعيين الجلسة في حالة حدوث خطأ في قاعدة البيانات
            try:
                db.session.rollback()
            except:
                pass

def handle_message(message):
    """معالجة الرسائل الواردة"""
    try:
        # تسجيل الرسالة - نقلناها إلى بلوك try/except منفصل
        # لتجنب توقف معالجة الرسالة إذا فشل التسجيل
        log_message(message, "receive")
    except Exception as e:
        logger.error(f"فشل تسجيل الرسالة وتم المتابعة: {e}")
        # إعادة تعيين الجلسة بعد الخطأ
        db.session.rollback()
    
    try:
        # معالجة المستخدم
        user = handle_user(message["from"])
        
        # تحديث نشاط المستخدم
        if user:
            user.update_activity()
        
        # التحقق من نوع الرسالة
        if "text" in message:
            # استلام أمر
            if message["text"].startswith("/"):
                handle_command(message)
            # رسالة عادية
            else:
                handle_text_message(message)
        elif "new_chat_members" in message:
            handle_new_chat_members(message)
        elif "left_chat_member" in message:
            handle_left_chat_member(message)
    except Exception as e:
        logger.error(f"خطأ في معالجة الرسالة: {e}")
        # إعادة تعيين الجلسة بعد الخطأ
        db.session.rollback()

def handle_command(message):
    """معالجة الأوامر"""
    command = message["text"].split()[0].lower()
    
    try:
        # التحقق من نوع الدردشة
        if "chat" in message and message["chat"]["type"] == "private":
            # توجيه مباشرة إلى معالج الرسائل الخاصة
            from study_bot.bot.handlers.private import handle_private_message
            handle_private_message(message)
        else:
            # معالجة أوامر المجموعة
            try:
                # استخراج معلومات رسالة المجموعة
                user_id = message.get("from", {}).get("id")
                chat_id = message.get("chat", {}).get("id")
                text = message.get("text", "")
                chat_type = message.get("chat", {}).get("type", "")
                
                from study_bot.bot.handlers.groups import handle_group_message
                handle_group_message(message, user_id, chat_id, text, chat_type)
            except Exception as e:
                logger.error(f"حدث خطأ أثناء معالجة أمر المجموعة: {e}")
    except Exception as e:
        logger.error(f"حدث خطأ عام أثناء معالجة الأمر: {e}")

def handle_text_message(message):
    """معالجة الرسائل النصية العادية"""
    # التحقق من نوع الدردشة
    if "chat" in message and message["chat"]["type"] == "private":
        from study_bot.bot.handlers.private import handle_private_message
        handle_private_message(message)
    else:
        try:
            from study_bot.bot.handlers.groups import handle_group_message
            
            # استخراج البيانات المطلوبة لمعالجة الرسالة
            user_id = message.get("from", {}).get("id")
            chat_id = message.get("chat", {}).get("id")
            text = message.get("text", "")
            chat_type = message.get("chat", {}).get("type")
            
            # استدعاء دالة معالجة رسائل المجموعة مع جميع الوسائط المطلوبة
            handle_group_message(message, user_id, chat_id, text, chat_type)
        except Exception as e:
            logger.error(f"حدث خطأ أثناء معالجة رسالة المجموعة: {e}")

def handle_callback_query(callback_query):
    """معالجة استجابات الأزرار"""
    from study_bot.bot.handlers.callbacks import handle_callback_query as process_callback
    process_callback(callback_query)

def handle_chat_member(chat_member_update):
    """معالجة تحديثات أعضاء الدردشة"""
    from study_bot.bot.handlers.chat_member import handle_chat_member_update
    handle_chat_member_update(chat_member_update)

def handle_new_chat_members(message):
    """معالجة الأعضاء الجدد في الدردشة"""
    from study_bot.bot.handlers.groups import handle_new_members
    handle_new_members(message)

def handle_left_chat_member(message):
    """معالجة الأعضاء المغادرين للدردشة"""
    from study_bot.bot.handlers.groups import handle_left_member
    handle_left_member(message)

def handle_user(user_data):
    """معالجة بيانات المستخدم"""
    try:
        # البحث عن المستخدم
        user = User.query.filter_by(telegram_id=user_data["id"]).first()
        
        # إضافة مستخدم جديد إذا لم يكن موجودًا
        if not user:
            try:
                user = User(
                    telegram_id=user_data["id"],
                    username=user_data.get("username"),
                    first_name=user_data.get("first_name"),
                    last_name=user_data.get("last_name"),
                    is_admin=False,
                    is_active=True,
                    language_code=user_data.get("language_code", "ar"),
                    registration_date=datetime.now(SCHEDULER_TIMEZONE)
                )
                db.session.add(user)
                db.session.commit()
                
                logger.info(f"تم إضافة مستخدم جديد: {user.get_full_name()} (ID: {user.telegram_id})")
            except Exception as e:
                logger.error(f"خطأ في إضافة مستخدم جديد: {e}")
                db.session.rollback()
                # محاولة إرجاع المستخدم الموجود بالفعل أو None
                return User.query.filter_by(telegram_id=user_data["id"]).first()
        else:
            try:
                # تحديث بيانات المستخدم إذا تغيرت
                updated = False
                
                if user.username != user_data.get("username"):
                    user.username = user_data.get("username")
                    updated = True
                
                if user.first_name != user_data.get("first_name"):
                    user.first_name = user_data.get("first_name")
                    updated = True
                
                if user.last_name != user_data.get("last_name"):
                    user.last_name = user_data.get("last_name")
                    updated = True
                
                if user.language_code != user_data.get("language_code", user.language_code):
                    user.language_code = user_data.get("language_code", user.language_code)
                    updated = True
                
                if updated:
                    db.session.commit()
            except Exception as e:
                logger.error(f"خطأ في تحديث بيانات المستخدم: {e}")
                db.session.rollback()
        
        return user
    except Exception as e:
        logger.error(f"خطأ عام في معالجة بيانات المستخدم: {e}")
        # إعادة تعيين الجلسة
        try:
            db.session.rollback()
        except:
            pass
        
        # محاولة إعادة المستخدم حتى مع حدوث خطأ
        try:
            return User.query.filter_by(telegram_id=user_data["id"]).first()
        except:
            return None

def send_message(chat_id, text, reply_markup=None, parse_mode="HTML"):
    """إرسال رسالة إلى مستخدم أو مجموعة"""
    try:
        # بناء رابط الطلب مع التأكد من إضافة التوكن
        url = f"{TELEGRAM_API_URL}/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        
        # بناء البيانات
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode  # استخدام HTML كقيمة افتراضية لتنسيق الرسائل
        }
        
        # إضافة لوحة المفاتيح إذا تم تقديمها
        if reply_markup:
            data["reply_markup"] = reply_markup if isinstance(reply_markup, str) else json.dumps(reply_markup)
        
        # إرسال الطلب
        response = requests.post(url, json=data, timeout=60)
        
        # التحقق من نجاح الطلب
        if response.status_code != 200:
            logger.error(f"فشل إرسال الرسالة: {response.text}")
            return None
        
        # تحليل الاستجابة
        result = response.json()
        
        if not result["ok"]:
            logger.error(f"خطأ في إرسال الرسالة: {result}")
            return None
        
        # تسجيل الرسالة المرسلة
        sent_message = result["result"]
        
        try:
            # إنشاء سجل للرسالة المرسلة
            message_log = MessageLog(
                chat_id=chat_id,
                user_id=None,  # الرسائل المرسلة من البوت ليس لها معرف مستخدم
                message_type="send",
                message_id=sent_message["message_id"],
                content=text,
                is_from_bot=True,
                sent_at=datetime.now(SCHEDULER_TIMEZONE)
            )
            
            db.session.add(message_log)
            db.session.commit()
        except Exception as e:
            logger.error(f"حدث خطأ أثناء تسجيل الرسالة المرسلة: {e}")
            # إعادة تعيين الجلسة في حالة حدوث خطأ لتجنب الخطأ في العمليات اللاحقة
            try:
                db.session.rollback()
            except:
                pass
        
        return sent_message
    except Exception as e:
        logger.error(f"حدث خطأ أثناء إرسال الرسالة: {e}")
        return None

def edit_message(chat_id, message_id, text, reply_markup=None, parse_mode="HTML"):
    """تعديل رسالة موجودة"""
    try:
        # بناء رابط الطلب مع التأكد من إضافة التوكن
        url = f"{TELEGRAM_API_URL}/bot{TELEGRAM_BOT_TOKEN}/editMessageText"
        
        # بناء البيانات
        data = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": parse_mode
        }
        
        # إضافة لوحة المفاتيح إذا تم تقديمها
        if reply_markup:
            data["reply_markup"] = reply_markup if isinstance(reply_markup, str) else json.dumps(reply_markup)
        
        # إرسال الطلب
        response = requests.post(url, json=data, timeout=60)
        
        # التحقق من نجاح الطلب
        if response.status_code != 200:
            logger.error(f"فشل تعديل الرسالة: {response.text}")
            return None
        
        # تحليل الاستجابة
        result = response.json()
        
        if not result["ok"]:
            logger.error(f"خطأ في تعديل الرسالة: {result}")
            return None
        
        # تسجيل الرسالة المعدلة
        edited_message = result["result"]
        
        try:
            # تحديث سجل الرسالة
            message_log = MessageLog.query.filter_by(
                chat_id=chat_id,
                message_id=message_id
            ).first()
            
            if message_log:
                message_log.content = text
                message_log.updated_at = datetime.now(SCHEDULER_TIMEZONE)
                db.session.commit()
            else:
                # إنشاء سجل جديد إذا لم يكن موجودًا
                new_log = MessageLog(
                    chat_id=chat_id,
                    user_id=None,
                    message_type="edit",
                    message_id=message_id,
                    content=text,
                    is_from_bot=True,
                    sent_at=datetime.now(SCHEDULER_TIMEZONE)
                )
                db.session.add(new_log)
                db.session.commit()
        except Exception as e:
            logger.error(f"حدث خطأ أثناء تسجيل الرسالة المعدلة: {e}")
            try:
                db.session.rollback()
            except:
                pass
        
        return edited_message
    except Exception as e:
        logger.error(f"حدث خطأ أثناء تعديل الرسالة: {e}")
        return None

def log_message(message, message_type="receive"):
    """تسجيل الرسالة"""
    try:
        # تجهيز بيانات الرسالة
        chat_id = message.get("chat", {}).get("id") if "chat" in message else None
        message_id = message.get("message_id")
        message_text = message.get("text", "") if "text" in message else ""
        user_id = message.get("from", {}).get("id") if "from" in message else None
        
        if not chat_id or not message_id:
            return
        
        # إنشاء سجل للرسالة - استخدم عمود content بدلاً من message_text لتتوافق مع بنية الجدول
        message_log = MessageLog(
            chat_id=chat_id,
            user_id=user_id,
            message_type=message_type,
            message_id=message_id,
            content=message_text,
            is_from_bot=False,
            sent_at=datetime.now(SCHEDULER_TIMEZONE)
        )
        
        db.session.add(message_log)
        db.session.commit()
    except Exception as e:
        logger.error(f"حدث خطأ أثناء تسجيل الرسالة: {e}")