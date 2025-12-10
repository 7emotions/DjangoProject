# parser_app/admin.py
from django.contrib import admin
from .models import ImageUpload, ParseResult
from django.utils.html import format_html
from django.db.models import Count
from django.contrib import messages
from django.http import HttpResponseRedirect
import requests
import base64
import os
from django.conf import settings


class ParseResultInline(admin.TabularInline):
    """在ImageUpload中内联显示ParseResult"""
    model = ParseResult
    extra = 0
    readonly_fields = ['created_at', 'pruned_result_preview', 'markdown_preview']
    fields = ['result_index', 'pruned_result_preview', 'markdown_preview', 'created_at']
    can_delete = False
    max_num = 10  # 最多显示10个结果

    def pruned_result_preview(self, obj):
        """精简结果预览"""
        if obj.pruned_result:
            preview = obj.pruned_result[:100]
            if len(obj.pruned_result) > 100:
                preview += '...'
            return preview
        return '-'

    pruned_result_preview.short_description = '精简结果预览'

    def markdown_preview(self, obj):
        """Markdown预览"""
        if obj.markdown_text:
            preview = obj.markdown_text[:100]
            if len(obj.markdown_text) > 100:
                preview += '...'
            return preview
        return '-'

    markdown_preview.short_description = 'Markdown预览'

    def has_add_permission(self, request, obj=None):
        """禁止添加"""
        return False

    def has_change_permission(self, request, obj=None):
        """禁止修改"""
        return False


@admin.register(ImageUpload)
class ImageUploadAdmin(admin.ModelAdmin):
    """图片上传记录管理"""
    # 将actions定义为一个属性（列表），而不是方法
    actions = ['mark_as_completed', 'mark_as_failed', 'retry_processing']

    list_display = ['id', 'original_filename', 'file_size_display', 'upload_time_display',
                    'status_display', 'results_count', 'processing_time_display',
                    'image_preview_link', 'admin_actions']
    list_filter = ['status', 'upload_time']
    search_fields = ['original_filename', 'ip_address', 'error_message']
    readonly_fields = ['id', 'upload_time', 'processing_time', 'ip_address',
                       'user_agent', 'error_message', 'image_preview',
                       'file_size_display', 'duration_display', 'results_count_display']
    fieldsets = (
        ('基本信息', {
            'fields': ('id', 'original_filename', 'image', 'image_preview',
                       'file_size_display', 'upload_time')
        }),
        ('处理信息', {
            'fields': ('status', 'processing_time', 'duration_display',
                       'results_count_display', 'error_message')
        }),
        ('系统信息', {
            'fields': ('ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
    )
    inlines = [ParseResultInline]
    list_per_page = 20
    date_hierarchy = 'upload_time'

    def upload_time_display(self, obj):
        """格式化上传时间"""
        return obj.upload_time.strftime('%Y-%m-%d %H:%M:%S')

    upload_time_display.short_description = '上传时间'
    upload_time_display.admin_order_field = 'upload_time'

    def file_size_display(self, obj):
        """文件大小显示"""
        return obj.get_file_size_display()

    file_size_display.short_description = '文件大小'

    def status_display(self, obj):
        """带颜色的状态显示"""
        colors = {
            'pending': 'orange',
            'processing': 'blue',
            'completed': 'green',
            'failed': 'red',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )

    status_display.short_description = '状态'

    def results_count(self, obj):
        """结果数量"""
        count = obj.results.count()
        color = 'green' if count > 0 else 'gray'
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            count
        )

    results_count.short_description = '结果数量'

    def processing_time_display(self, obj):
        """处理时间显示"""
        if obj.processing_time:
            return f"{obj.processing_time:.2f}秒"
        return '-'

    processing_time_display.short_description = '处理时间'

    def image_preview_link(self, obj):
        """图片预览链接"""
        if obj.image:
            return format_html(
                '<a href="{}" target="_blank" style="padding: 2px 8px; background: #417690; color: white; text-decoration: none; border-radius: 3px;">查看图片</a>',
                obj.image.url
            )
        return '-'

    image_preview_link.short_description = '图片预览'

    def admin_actions(self, obj):
        """操作按钮"""
        buttons = []

        # 查看详情按钮
        buttons.append(
            format_html(
                '<a href="/admin/parser_app/imageupload/{}/change/" class="button" style="padding: 2px 8px; background: #417690; color: white; text-decoration: none; border-radius: 3px; margin-right: 5px;">查看</a>',
                obj.id
            )
        )

        # 删除按钮
        buttons.append(
            format_html(
                '<a href="/admin/parser_app/imageupload/{}/delete/" class="button" style="padding: 2px 8px; background: #ba2121; color: white; text-decoration: none; border-radius: 3px;">删除</a>',
                obj.id
            )
        )

        return format_html(' '.join(buttons))

    admin_actions.short_description = '操作'

    def image_preview(self, obj):
        """图片预览"""
        if obj.image and hasattr(obj.image, 'url'):
            try:
                return format_html(
                    '<img src="{}" style="max-width: 300px; max-height: 200px;" />',
                    obj.image.url
                )
            except:
                return '图片路径错误'
        return '无图片'

    image_preview.short_description = '图片预览'

    def duration_display(self, obj):
        """处理时长显示"""
        if obj.processing_time:
            return f"{obj.processing_time:.2f}秒"
        return '-'

    duration_display.short_description = '处理时长'

    def results_count_display(self, obj):
        """结果数量显示"""
        count = obj.results.count()
        return f"{count} 个"

    results_count_display.short_description = '结果数量'

    # 自定义动作方法
    def mark_as_completed(self, request, queryset):
        """标记为已完成"""
        updated = queryset.update(status='completed')
        self.message_user(request, f"成功标记 {updated} 条记录为已完成", messages.SUCCESS)

    mark_as_completed.short_description = "标记为已完成"

    def mark_as_failed(self, request, queryset):
        """标记为失败"""
        updated = queryset.update(status='failed', error_message='管理员手动标记为失败')
        self.message_user(request, f"成功标记 {updated} 条记录为失败", messages.WARNING)

    mark_as_failed.short_description = "标记为失败"

    def retry_processing(self, request, queryset):
        """重新处理选中的记录"""
        for record in queryset:
            if record.status in ['failed', 'pending'] and record.image:
                try:
                    # 重新处理逻辑
                    record.status = 'processing'
                    record.error_message = ''
                    record.save()

                    # 这里可以调用API重新处理
                    # self._process_image(record)

                except Exception as e:
                    self.message_user(request, f"处理记录 {record.id} 时出错: {str(e)}", messages.ERROR)
                    continue

        self.message_user(request, f"已开始重新处理 {queryset.count()} 条记录", messages.SUCCESS)

        # 返回当前页面
        return HttpResponseRedirect(request.get_full_path())

    retry_processing.short_description = "重新处理"

    def _process_image(self, record):
        """处理图片的内部方法"""
        # 这里实现实际的图片处理逻辑
        API_URL = "http://44239ef8.r20.cpolar.top/layout-parsing"

        try:
            # 读取图片
            image_path = record.image.path
            with open(image_path, "rb") as file:
                image_bytes = file.read()
                image_data = base64.b64encode(image_bytes).decode("ascii")

            # 调用API
            payload = {
                "file": image_data,
                "fileType": 1,
            }

            response = requests.post(API_URL, json=payload, timeout=60)

            if response.status_code == 200:
                record.status = 'completed'
                record.processing_time = 0  # 可以设置实际的处理时间
                record.save()

                # 保存解析结果
                result_data = response.json()
                # ... 保存结果的逻辑

            else:
                record.status = 'failed'
                record.error_message = f"API请求失败: {response.status_code}"
                record.save()

        except Exception as e:
            record.status = 'failed'
            record.error_message = f"处理失败: {str(e)}"
            record.save()

    def get_queryset(self, request):
        """优化查询"""
        queryset = super().get_queryset(request)
        queryset = queryset.prefetch_related('results')
        return queryset


@admin.register(ParseResult)
class ParseResultAdmin(admin.ModelAdmin):
    """解析结果管理"""
    actions = []  # 空列表，没有批量操作

    list_display = ['id', 'image_link', 'result_index', 'pruned_result_preview',
                    'markdown_preview', 'output_images_count', 'created_at_display']
    list_filter = ['created_at', 'image__status']
    search_fields = ['pruned_result', 'markdown_text', 'image__original_filename']
    readonly_fields = ['id', 'created_at', 'image_link', 'pruned_result_full',
                       'markdown_full', 'raw_data_preview', 'output_images_count']
    fieldsets = (
        ('基本信息', {
            'fields': ('id', 'image_link', 'result_index', 'created_at', 'output_images_count')
        }),
        ('解析结果', {
            'fields': ('pruned_result_full', 'markdown_full')
        }),
        ('原始数据', {
            'fields': ('raw_data_preview',),
            'classes': ('collapse',)
        }),
    )
    list_per_page = 20
    date_hierarchy = 'created_at'

    def image_link(self, obj):
        """链接到对应的ImageUpload"""
        return format_html(
            '<a href="/admin/parser_app/imageupload/{}/change/">{}</a>',
            obj.image.id,
            obj.image.original_filename
        )

    image_link.short_description = '原始图片'

    def pruned_result_preview(self, obj):
        """精简结果预览"""
        if obj.pruned_result:
            preview = obj.pruned_result[:50]
            if len(obj.pruned_result) > 50:
                preview += '...'
            return preview
        return '-'

    pruned_result_preview.short_description = '精简结果'

    def markdown_preview(self, obj):
        """Markdown预览"""
        if obj.markdown_text:
            preview = obj.markdown_text[:50]
            if len(obj.markdown_text) > 50:
                preview += '...'
            return preview
        return '-'

    markdown_preview.short_description = 'Markdown'

    def created_at_display(self, obj):
        """创建时间显示"""
        return obj.created_at.strftime('%Y-%m-%d %H:%M:%S')

    created_at_display.short_description = '创建时间'
    created_at_display.admin_order_field = 'created_at'

    def pruned_result_full(self, obj):
        """完整的精简结果"""
        if obj.pruned_result:
            return format_html(
                '<div style="max-height: 200px; overflow-y: auto; padding: 10px; background: #f5f5f5; border: 1px solid #ddd; border-radius: 4px; font-family: monospace; white-space: pre-wrap;">{}</div>',
                obj.pruned_result
            )
        return '-'

    pruned_result_full.short_description = '完整的精简结果'

    def markdown_full(self, obj):
        """完整的Markdown"""
        if obj.markdown_text:
            return format_html(
                '<div style="max-height: 300px; overflow-y: auto; padding: 10px; background: #f5f5f5; border: 1px solid #ddd; border-radius: 4px; font-family: monospace; white-space: pre-wrap;">{}</div>',
                obj.markdown_text
            )
        return '-'

    markdown_full.short_description = '完整的Markdown'

    def raw_data_preview(self, obj):
        """原始数据预览"""
        if obj.raw_data:
            import json
            try:
                formatted = json.dumps(obj.raw_data, indent=2, ensure_ascii=False)
                return format_html(
                    '<div style="max-height: 400px; overflow-y: auto; padding: 10px; background: #2d2d2d; color: #f8f8f2; border-radius: 4px; font-family: monospace; white-space: pre-wrap;">{}</div>',
                    formatted
                )
            except:
                return str(obj.raw_data)[:500] + '...'
        return '-'

    raw_data_preview.short_description = '原始数据'

    def get_queryset(self, request):
        """优化查询"""
        queryset = super().get_queryset(request)
        queryset = queryset.select_related('image')
        return queryset

    def has_add_permission(self, request):
        """禁止添加"""
        return False

    def has_change_permission(self, request, obj=None):
        """禁止修改"""
        return False


# 可选：自定义管理站点标题
admin.site.site_header = 'OCR服务管理系统'
admin.site.site_title = 'OCR服务管理'
admin.site.index_title = '数据管理'