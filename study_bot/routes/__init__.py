#!/usr/bin/env python3
"""
وحدة مسارات التطبيق
تحتوي على جميع مسارات واجهة الويب وواجهة برمجة التطبيقات
"""

from flask import Blueprint

# إنشاء blueprints للمسارات
main_bp = Blueprint('main', __name__)
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
users_bp = Blueprint('users', __name__, url_prefix='/users')
camps_bp = Blueprint('camps', __name__, url_prefix='/camps')
stats_bp = Blueprint('stats', __name__, url_prefix='/stats')

# استيراد المسارات
from . import main, admin, users, camps, stats

def register_blueprints(app):
    """تسجيل جميع blueprints مع التطبيق"""
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(camps_bp)
    app.register_blueprint(stats_bp)
    
    return app
