# parser_app/templatetags/custom_filters.py
from django import template
import os
from django.conf import settings

register = template.Library()

@register.filter
def addstring(value, arg):
    """字符串连接过滤器"""
    return str(value) + str(arg)

@register.filter
def file_exists(filepath):
    """检查文件是否存在"""
    full_path = os.path.join(settings.MEDIA_ROOT, filepath)
    return os.path.exists(full_path)

@register.filter
def get_item(dictionary, key):
    """从字典中获取项"""
    return dictionary.get(key)

@register.filter
def filename(value):
    """获取文件名"""
    return os.path.basename(value)