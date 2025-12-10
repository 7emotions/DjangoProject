# parser_app/models.py
from django.db import models
from DjangoPaddleOCR import settings
import os
import uuid


def user_directory_path(instance, filename):
    """文件上传路径"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4().hex[:10]}.{ext}"
    return os.path.join('uploads', filename)


class ImageUpload(models.Model):
    """上传的图片模型"""
    STATUS_CHOICES = [
        ('pending', '待处理'),
        ('processing', '处理中'),
        ('completed', '已完成'),
        ('failed', '失败'),
    ]

    image = models.ImageField(upload_to=user_directory_path, verbose_name='图片文件')
    original_filename = models.CharField(max_length=255, verbose_name='原始文件名')
    file_size = models.BigIntegerField(verbose_name='文件大小', help_text='字节')
    upload_time = models.DateTimeField(auto_now_add=True, verbose_name='上传时间')  # 这里使用upload_time
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='状态')
    error_message = models.TextField(blank=True, verbose_name='错误信息')
    processing_time = models.FloatField(null=True, blank=True, verbose_name='处理时间(秒)')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP地址')
    user_agent = models.TextField(blank=True, verbose_name='用户代理')

    class Meta:
        ordering = ['-upload_time']
        verbose_name = '图片上传记录'
        verbose_name_plural = '图片上传记录'

    def __str__(self):
        return f"{self.original_filename} ({self.upload_time.strftime('%Y-%m-%d %H:%M')})"

    def get_file_size_display(self):
        """显示友好的文件大小"""
        if self.file_size < 1024:
            return f"{self.file_size} B"
        elif self.file_size < 1024 * 1024:
            return f"{self.file_size / 1024:.1f} KB"
        elif self.file_size < 1024 * 1024 * 1024:
            return f"{self.file_size / (1024 * 1024):.1f} MB"
        else:
            return f"{self.file_size / (1024 * 1024 * 1024):.1f} GB"


class ParseResult(models.Model):
    """解析结果模型"""
    image = models.ForeignKey(ImageUpload, on_delete=models.CASCADE, related_name='results', verbose_name='原始图片')
    result_index = models.IntegerField(default=0, verbose_name='结果索引')
    pruned_result = models.TextField(verbose_name='精简结果')
    markdown_text = models.TextField(verbose_name='Markdown内容')
    output_images_count = models.IntegerField(default=0, verbose_name='输出图片数量')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    raw_data = models.JSONField(null=True, blank=True, verbose_name='原始数据')

    markdown_image_paths = models.JSONField(default=list, verbose_name='Markdown图片路径')
    output_image_paths = models.JSONField(default=list, verbose_name='输出图片路径')

    class Meta:
        ordering = ['-created_at']
        verbose_name = '解析结果'
        verbose_name_plural = '解析结果'
        unique_together = ['image', 'result_index']

    def __str__(self):
        return f"{self.image.original_filename} - 结果{self.result_index}"

    def get_markdown_preview(self):
        """获取Markdown预览（前200字符）"""
        if self.markdown_text:
            preview = self.markdown_text[:200]
            if len(self.markdown_text) > 200:
                preview += '...'
            return preview
        return ''

    @property
    def markdown_images_count(self):
        """Markdown图片数量"""
        return len(self.markdown_image_paths)

    @property
    def output_images_count(self):
        """输出图片数量"""
        return len(self.output_image_paths)

    def get_markdown_images_info(self):
        """获取Markdown图片详细信息"""
        images_info = []
        for img_path in self.markdown_image_paths:
            # 提取文件名
            filename = os.path.basename(img_path) if img_path else 'unknown'
            # 构建完整URL路径
            relative_path = f"markdown_{self.image.id}_{self.result_index}/imgs/{img_path}"
            images_info.append({
                'path': img_path,
                'filename': filename,
                'url': f"{settings.MEDIA_URL}{relative_path}",
                'relative_path': relative_path
            })
        return images_info

    def get_output_images_info(self):
        """获取输出图片详细信息"""
        images_info = []
        for img_path in self.output_image_paths:
            # 提取文件名
            filename = os.path.basename(img_path) if img_path else 'unknown'
            images_info.append({
                'path': img_path,
                'filename': filename,
                'url': f"{settings.MEDIA_URL}{img_path}"
            })
        return images_info