#!/usr/bin/env python3
"""
مسارات الواجهة الرئيسية
تحتوي على المسارات الأساسية للتطبيق
"""

from flask import render_template, redirect, url_for, request
from . import main_bp

@main_bp.route('/')
def index():
    """الصفحة الرئيسية"""
    return render_template('index.html', title='بوت الدراسة والتحفيز')

@main_bp.route('/dashboard')
def dashboard():
    """لوحة التحكم"""
    return render_template('dashboard.html', title='لوحة التحكم')

@main_bp.route('/about')
def about():
    """حول التطبيق"""
    return render_template('about.html', title='حول البوت')

@main_bp.route('/help')
def help_page():
    """صفحة المساعدة"""
    return render_template('help.html', title='المساعدة')

@main_bp.route('/error')
def error():
    """صفحة الخطأ"""
    error_message = request.args.get('message', 'حدث خطأ غير معروف')
    return render_template('error.html', title='خطأ', error_message=error_message)

@main_bp.route('/health')
def health():
    """فحص صحة التطبيق"""
    return {'status': 'ok'}
