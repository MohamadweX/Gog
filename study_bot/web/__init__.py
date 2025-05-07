"""
وحدة الويب
تحتوي على وظائف الواجهة الويب للتطبيق
"""

import os
import json
import logging
from datetime import datetime, timedelta

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix

from study_bot.config import logger

# إنشاء blueprint للمسارات الرئيسية
main_bp = Blueprint('main', __name__)

# تعريف المسارات قبل التسجيل
@main_bp.route('/')
def index():
    """صفحة البداية"""
    return render_template('index.html')

@main_bp.route('/dashboard')
def dashboard():
    """لوحة التحكم"""
    from study_bot.models import Group, User
    
    # إحصائيات عامة
    total_users = User.query.filter_by(is_active=True).count()
    total_groups = Group.query.filter_by(is_active=True).count()
    
    # إحصائيات المعسكرات
    from study_bot.models import CustomCamp, CampTask
    active_camps = CustomCamp.query.filter_by(is_active=True).count()
    
    # الإحصائيات العامة
    from study_bot.models import SystemStat
    messages_sent = SystemStat.get('messages_sent', 0)
    
    stats = {
        'total_users': total_users,
        'total_groups': total_groups,
        'active_camps': active_camps,
        'messages_sent': messages_sent
    }
    
    return render_template('dashboard.html', stats=stats)

@main_bp.route('/groups')
def groups():
    """صفحة المجموعات"""
    from study_bot.models import Group
    groups = Group.query.filter_by(is_active=True).all()
    return render_template('groups.html', groups=groups)

@main_bp.route('/users')
def users():
    """صفحة المستخدمين"""
    from study_bot.models import User
    users = User.query.filter_by(is_active=True).all()
    return render_template('users.html', users=users)

@main_bp.route('/camps')
def camps():
    """صفحة المعسكرات"""
    from study_bot.models import CustomCamp
    camps = CustomCamp.query.filter_by(is_active=True).all()
    return render_template('camps.html', camps=camps)

@main_bp.route('/send_broadcast', methods=['GET', 'POST'])
def send_broadcast():
    """صفحة إرسال رسالة جماعية"""
    if request.method == 'POST':
        message = request.form.get('message')
        if message:
            from study_bot.bot import send_broadcast_message
            result = send_broadcast_message(message)
            flash(f'تم إرسال الرسالة إلى {result} مستخدم', 'success')
        else:
            flash('الرجاء إدخال نص الرسالة', 'danger')
    
    return render_template('send_broadcast.html')

# إضافة مسارات API
@main_bp.route('/api/stats')
def api_stats():
    """إحصائيات API"""
    from study_bot.models import SystemStat, User, Group, CustomCamp
    
    stats = {
        'total_users': User.query.filter_by(is_active=True).count(),
        'total_groups': Group.query.filter_by(is_active=True).count(),
        'active_camps': CustomCamp.query.filter_by(is_active=True).count(),
        'messages_sent': SystemStat.get('messages_sent', 0),
        'updated_at': datetime.utcnow().isoformat()
    }
    
    return jsonify(stats)

# دالة لتهيئة واجهة الويب
def init_web(app):
    """تهيئة واجهة الويب"""
    try:
        # إعداد تصحيح عناوين البروكسي
        app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
        
        # تسجيل blueprints
        app.register_blueprint(main_bp)
        
        # تسجيل معالجات الأخطاء
        @app.errorhandler(404)
        def page_not_found(e):
            """صفحة 404"""
            return render_template('404.html'), 404
        
        @app.errorhandler(500)
        def server_error(e):
            """صفحة 500"""
            return render_template('500.html'), 500
        
        logger.info("تم تهيئة واجهة الويب")
        return app
    except Exception as e:
        logger.error(f"خطأ في تهيئة واجهة الويب: {e}")
        return app