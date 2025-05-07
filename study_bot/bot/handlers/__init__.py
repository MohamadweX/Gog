"""
وحدة معالجات البوت
يحتوي على معالجات رسائل تيليجرام والاستجابات
"""

from study_bot.config import logger

def register_handlers():
    """تسجيل معالجات البوت"""
    logger.info("تسجيل معالجات البوت")
    
    # استيراد معالجات الرسائل والاستجابات
    from study_bot.bot.handlers import message, callback, chat_member
    
    return True