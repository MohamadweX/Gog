#!/usr/bin/env python3
"""
ملف البداية الرئيسي للتطبيق
يدير تهيئة التطبيق وتشغيل البوت والويب سيرفر
"""

import logging
from study_bot import create_app

# إعداد التسجيل للتصحيح
logging.basicConfig(level=logging.DEBUG)

# إنشاء التطبيق
app = create_app()

if __name__ == "__main__":
    # تشغيل التطبيق عند استدعاء الملف مباشرة
    app.run(host="0.0.0.0", port=5000, debug=True)
