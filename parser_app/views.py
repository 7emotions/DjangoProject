from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.utils import timezone
from django.views.decorators.http import require_POST
from .models import ImageUpload, ParseResult
import base64
import requests
import os
import json
from datetime import datetime, timedelta
import logging
import time
import uuid

logger = logging.getLogger(__name__)

API_URL = "http://60590ca1.r20.cpolar.top/layout-parsing"

def conversion_history(request):
    """转换记录页面"""
    # 获取查询参数
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    # 获取所有记录
    records = ImageUpload.objects.all().order_by('-upload_time')

    # 应用过滤器
    if search_query:
        records = records.filter(
            Q(original_filename__icontains=search_query) |
            Q(results__pruned_result__icontains=search_query) |
            Q(results__markdown_text__icontains=search_query)
        ).distinct()

    if status_filter:
        records = records.filter(status=status_filter)

    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            records = records.filter(upload_time__date__gte=date_from_obj)
        except ValueError:
            pass

    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
            records = records.filter(upload_time__date__lte=date_to_obj)
        except ValueError:
            pass

    # 分页
    page = request.GET.get('page', 1)
    paginator = Paginator(records, 20)  # 每页20条

    try:
        records_page = paginator.page(page)
    except PageNotAnInteger:
        records_page = paginator.page(1)
    except EmptyPage:
        records_page = paginator.page(paginator.num_pages)

    # 统计信息
    total_count = ImageUpload.objects.count()
    completed_count = ImageUpload.objects.filter(status='completed').count()
    failed_count = ImageUpload.objects.filter(status='failed').count()
    pending_count = ImageUpload.objects.filter(status='pending').count()

    # 今日统计
    today = timezone.now().date()
    today_records = ImageUpload.objects.filter(upload_time__date=today)
    today_count = today_records.count()
    today_completed = today_records.filter(status='completed').count()

    context = {
        'records': records_page,
        'total_count': total_count,
        'completed_count': completed_count,
        'failed_count': failed_count,
        'pending_count': pending_count,
        'today_count': today_count,
        'today_completed': today_completed,
        'search_query': search_query,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'status_choices': ImageUpload.STATUS_CHOICES,
    }

    return render(request, 'conversion_history.html', context)


def record_detail(request, record_id):
    """转换记录详情"""
    record = get_object_or_404(ImageUpload, id=record_id)
    results = record.results.all()

    # 为每个结果准备图片URL信息
    for result in results:
        # Markdown图片信息
        result.markdown_images_info = []
        for img_path in result.markdown_image_paths:
            relative_path = f"markdown_{record.id}_{result.result_index}/{img_path}"
            result.markdown_images_info.append({
                'path': img_path,
                'filename': os.path.basename(img_path) if img_path else 'unknown',
                'url': f"{settings.MEDIA_URL}{record.image.name.split('/')[-1]}/{relative_path}",
                'full_path': os.path.join(settings.MEDIA_ROOT, relative_path)
            })

        # 输出图片信息
        result.output_images_info = []
        for img_path in result.output_image_paths:
            result.output_images_info.append({
                'path': img_path,
                'filename': os.path.basename(img_path) if img_path else 'unknown',
                'url': f"{settings.MEDIA_URL}{record.image.name.split('/')[-1]}/{img_path}",
                'full_path': os.path.join(settings.MEDIA_ROOT, img_path)
            })

    context = {
        'record': record,
        'results': results,
        'doc_dir': record.image.name.split('/')[-1],
        'MEDIA_URL': f"{settings.MEDIA_URL}"
    }

    return render(request, 'record_detail.html', context)


def delete_record(request, record_id):
    """删除转换记录"""
    if request.method == 'POST':
        record = get_object_or_404(ImageUpload, id=record_id)

        try:
            # 删除相关文件
            if record.image:
                if os.path.exists(record.image.path):
                    os.remove(record.image.path)

            # 删除解析结果相关的文件
            for result in record.results.all():
                # 删除markdown目录
                md_dir = os.path.join(settings.MEDIA_ROOT, f"markdown_{record.id}_{result.result_index}")
                if os.path.exists(md_dir):
                    import shutil
                    shutil.rmtree(md_dir)

                # 删除输出图片
                for img_name in ['output1', 'output2', 'output3']:  # 根据实际情况调整
                    img_path = os.path.join(settings.MEDIA_ROOT, f"{img_name}_{record.id}_{result.result_index}.jpg")
                    if os.path.exists(img_path):
                        os.remove(img_path)

            # 删除数据库记录
            record.delete()

            return JsonResponse({'success': True, 'message': '记录删除成功'})

        except Exception as e:
            logger.error(f"删除记录失败: {str(e)}")
            return JsonResponse({'success': False, 'error': f'删除失败: {str(e)}'})

    return JsonResponse({'success': False, 'error': '无效的请求方法'})


def bulk_delete_records(request):
    """批量删除记录"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            record_ids = data.get('record_ids', [])

            deleted_count = 0
            error_count = 0

            for record_id in record_ids:
                try:
                    record = ImageUpload.objects.get(id=record_id)

                    # 删除文件
                    if record.image and os.path.exists(record.image.path):
                        os.remove(record.image.path)

                    record.delete()
                    deleted_count += 1

                except Exception as e:
                    logger.error(f"删除记录 {record_id} 失败: {str(e)}")
                    error_count += 1

            return JsonResponse({
                'success': True,
                'message': f'成功删除 {deleted_count} 条记录，失败 {error_count} 条'
            })

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': '无效的请求方法'})


def export_records(request):
    """导出记录"""
    record_ids = request.GET.get('ids', '').split(',')

    if record_ids and record_ids[0]:
        records = ImageUpload.objects.filter(id__in=record_ids)
    else:
        records = ImageUpload.objects.all()

    # 创建CSV数据
    import csv
    from django.http import HttpResponse
    from io import StringIO

    # 创建内存文件
    csvfile = StringIO()
    writer = csv.writer(csvfile)

    # 写入表头
    writer.writerow(['ID', '文件名', '文件大小', '上传时间', '状态', '处理时间', '结果数量'])

    # 写入数据
    for record in records:
        writer.writerow([
            record.id,
            record.original_filename,
            record.get_file_size_display(),
            record.upload_time.strftime('%Y-%m-%d %H:%M:%S'),
            record.get_status_display(),
            f"{record.processing_time or 0:.2f}秒",
            record.results.count()
        ])

    # 创建HTTP响应
    response = HttpResponse(csvfile.getvalue(), content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="conversion_records.csv"'

    return response


def statistics_data(request):
    """统计数据的API"""
    # 获取时间范围
    days = int(request.GET.get('days', 30))

    # 计算日期范围
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)

    # 每日统计
    daily_stats = []
    for i in range(days):
        date = start_date + timedelta(days=i)
        day_records = ImageUpload.objects.filter(upload_time__date=date)

        daily_stats.append({
            'date': date.strftime('%Y-%m-%d'),
            'total': day_records.count(),
            'completed': day_records.filter(status='completed').count(),
            'failed': day_records.filter(status='failed').count(),
        })

    # 状态分布
    status_distribution = []
    for status_code, status_name in ImageUpload.STATUS_CHOICES:
        count = ImageUpload.objects.filter(status=status_code).count()
        if count > 0:
            status_distribution.append({
                'name': status_name,
                'value': count
            })

    # 文件大小分布
    size_ranges = [
        ('<100KB', 0, 100 * 1024),
        ('100KB-1MB', 100 * 1024, 1024 * 1024),
        ('1MB-5MB', 1024 * 1024, 5 * 1024 * 1024),
        ('5MB-10MB', 5 * 1024 * 1024, 10 * 1024 * 1024),
        ('>10MB', 10 * 1024 * 1024, None)
    ]

    size_distribution = []
    for name, min_size, max_size in size_ranges:
        if max_size:
            count = ImageUpload.objects.filter(file_size__gte=min_size, file_size__lt=max_size).count()
        else:
            count = ImageUpload.objects.filter(file_size__gte=min_size).count()

        size_distribution.append({
            'name': name,
            'value': count
        })

    return JsonResponse({
        'daily_stats': daily_stats,
        'status_distribution': status_distribution,
        'size_distribution': size_distribution,
    })
def index(request):
    """主页面"""
    return render(request, 'index.html')


@require_POST
def upload_image(request):
    """处理图片上传和解析"""
    try:
        # 检查是否有文件上传
        if 'image' not in request.FILES:
            logger.error("No file in request.FILES")
            return JsonResponse({'error': '没有上传文件'}, status=400)

        uploaded_file = request.FILES['image']
        logger.info(f"Received file: {uploaded_file.name}, size: {uploaded_file.size}")

        # 验证文件类型
        allowed_types = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/bmp']
        if uploaded_file.content_type not in allowed_types:
            logger.error(f"Invalid file type: {uploaded_file.content_type}")
            return JsonResponse({'error': '不支持的文件类型，请上传图片文件'}, status=400)

        # 验证文件大小（10MB）
        max_size = 10 * 1024 * 1024  # 10MB
        if uploaded_file.size > max_size:
            logger.error(f"File too large: {uploaded_file.size} bytes")
            return JsonResponse({'error': '文件大小不能超过10MB'}, status=400)

        # 保存文件
        fs = FileSystemStorage()

        # 生成唯一文件名
        ext = uploaded_file.name.split('.')[-1]
        filename = f"{uuid.uuid4().hex[:10]}.{ext}"

        # 保存文件并获取保存后的路径
        saved_filename = fs.save(f"{filename}\\{filename}", uploaded_file)
        file_path = os.path.join(f"{settings.MEDIA_ROOT}", saved_filename)

        # 获取客户端信息
        ip_address = request.META.get('REMOTE_ADDR', '')
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        # 创建ImageUpload记录
        image_record = ImageUpload.objects.create(
            image=saved_filename,
            original_filename=uploaded_file.name,
            file_size=uploaded_file.size,  # 确保提供file_size
            status='processing',
            ip_address=ip_address,
            user_agent=user_agent
        )

        try:
            # 读取并编码图片
            with open(file_path, "rb") as file:
                image_bytes = file.read()
                image_data = base64.b64encode(image_bytes).decode("ascii")

            logger.info(f"Image encoded, size: {len(image_data)} characters")

            # 准备API请求数据
            payload = {
                "file": image_data,
                "fileType": 1,
            }

            # 调用API，增加超时时间
            logger.info(f"Calling API: {API_URL}")
            start_time = time.time()

            try:
                response = requests.post(
                    API_URL,
                    json=payload,
                    timeout=120,  # 120秒超时
                    headers={
                        'Content-Type': 'application/json',
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                )

                elapsed_time = time.time() - start_time
                logger.info(f"API response received in {elapsed_time:.2f}s, status: {response.status_code}")

                # 更新处理时间
                image_record.processing_time = elapsed_time

                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"API returned result with keys: {list(result.keys())}")

                    if "result" in result:
                        results_data = result["result"]

                        save_results = []

                        # 处理每个解析结果
                        layout_results = results_data.get("layoutParsingResults", [])
                        for i, res in enumerate(layout_results):
                            markdown_image_paths=[]
                            images_data = res.get("markdown", {}).get("images", {})

                            # 保存markdown和图片
                            md_dir = os.path.join(f"{settings.MEDIA_ROOT}\\{filename}", f"markdown_{image_record.id}_{i}")
                            os.makedirs(md_dir, exist_ok=True)

                            # 保存markdown文本
                            md_path = os.path.join(md_dir, "doc.md")
                            with open(md_path, "w", encoding="utf-8") as f:
                                f.write(res.get("markdown", {}).get("text", ""))

                                # 保存Markdown图片并记录路径
                                for img_path, img_data in images_data.items():
                                    try:
                                        img_full_path = os.path.join(md_dir, img_path)
                                        os.makedirs(os.path.dirname(img_full_path), exist_ok=True)

                                        # 保存图片文件
                                        with open(img_full_path, "wb") as f:
                                            f.write(base64.b64decode(img_data))

                                        # 记录相对路径（相对于markdown目录）
                                        markdown_image_paths.append(img_path)

                                    except Exception as e:
                                        logger.error(f"保存Markdown图片失败: {str(e)}")
                                        continue

                                # 收集输出图片路径
                                output_image_paths = []
                                output_images_data = res.get("outputImages", {})

                                for img_name, img_data in output_images_data.items():
                                    try:
                                        # 生成输出图片文件名
                                        img_filename = f"{img_name}_{image_record.id}_{i}.jpg"
                                        output_path = os.path.join(f"{settings.MEDIA_ROOT}\\{filename}", img_filename)

                                        # 保存输出图片
                                        with open(output_path, "wb") as f:
                                            f.write(base64.b64decode(img_data))

                                        # 记录文件名
                                        output_image_paths.append(img_filename)

                                    except Exception as e:
                                        logger.error(f"保存输出图片失败: {str(e)}")
                                        continue

                            save_results.append({
                                'index': i,
                                'pruned_result': res.get("prunedResult", ""),
                                'markdown': res.get("markdown", {}).get("text", ""),
                                'markdown_dir': f"markdown_{image_record.id}_{i}",
                                'image_id': image_record.id
                            })

                            parse_result = ParseResult.objects.create(
                                image=image_record,
                                result_index=i,
                                pruned_result=res.get("prunedResult", ""),
                                markdown_text=res.get("markdown", {}).get("text", ""),
                                raw_data=res,
                                markdown_image_paths=markdown_image_paths,
                                output_image_paths=output_image_paths
                            )

                        # 更新状态为完成
                        image_record.status = 'completed'
                        image_record.save()

                        # 返回结果页面
                        context = {
                            'original_image': saved_filename,
                            'results': save_results,
                            'image_id': image_record.id,
                            'filename': uploaded_file.name,
                            'MEDIA_URL': settings.MEDIA_URL
                        }
                        return render(request, 'result.html', context)
                    else:
                        error_msg = f"API返回格式错误: {result}"
                        logger.error(error_msg)
                        image_record.status = 'failed'
                        image_record.error_message = error_msg[:500]
                        image_record.save()
                        return JsonResponse({'error': 'API返回数据格式不正确'}, status=500)
                else:
                    error_msg = f"API请求失败: {response.status_code}"
                    logger.error(error_msg)
                    image_record.status = 'failed'
                    image_record.error_message = error_msg[:500]
                    image_record.save()
                    return JsonResponse({
                        'error': f'API请求失败 (状态码: {response.status_code})',
                        'details': response.text[:200] if response.text else ''
                    }, status=500)

            except requests.exceptions.Timeout:
                error_msg = 'API请求超时，请稍后重试'
                logger.error(error_msg)
                image_record.status = 'failed'
                image_record.error_message = error_msg
                image_record.save()
                return JsonResponse({'error': error_msg}, status=504)
            except requests.exceptions.RequestException as e:
                error_msg = f'网络请求错误: {str(e)}'
                logger.error(error_msg)
                image_record.status = 'failed'
                image_record.error_message = error_msg[:500]
                image_record.save()
                return JsonResponse({'error': error_msg}, status=500)

        except Exception as e:
            error_msg = f'处理错误: {str(e)}'
            logger.error(f"Error processing file: {error_msg}", exc_info=True)
            image_record.status = 'failed'
            image_record.error_message = error_msg[:500]
            image_record.save()
            return JsonResponse({'error': error_msg}, status=500)

    except Exception as e:
        logger.error(f"Unexpected error in upload_image: {str(e)}", exc_info=True)
        return JsonResponse({'error': f'服务器内部错误: {str(e)}'}, status=500)


def api_parse(request):
    """API接口（用于AJAX调用）"""
    if request.method == 'POST':
        # 这里可以处理JSON格式的请求
        data = json.loads(request.body)
        image_data = data.get('image_data')

        if not image_data:
            return JsonResponse({'error': '没有图片数据'}, status=400)

        payload = {
            "file": image_data,
            "fileType": 1,
        }

        try:
            response = requests.post(API_URL, json=payload, timeout=30)
            return JsonResponse(response.json())
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': '只支持POST请求'}, status=400)


def result_detail(request, image_id, result_index):
    """查看详细结果"""
    try:
        parse_result = ParseResult.objects.get(
            image_id=image_id,
            result_index=result_index
        )

        context = {
            'result': parse_result,
            'original_image': parse_result.image.image.url if parse_result.image.image else '',
            'doc_dir': parse_result.image.image.url.split('/')[-1],
            'MEDIA_URL': f"{settings.MEDIA_URL}",
            'det_img': parse_result.output_image_paths[0] if parse_result.output_image_paths[0] else '',
            'order_img': parse_result.output_image_paths[1] if parse_result.output_image_paths[1] else '',
        }
        return render(request, 'detail.html', context)
    except ParseResult.DoesNotExist:
        return JsonResponse({'error': '结果不存在'}, status=404)