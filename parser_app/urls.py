# parser_app/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('upload/', views.upload_image, name='upload_image'),
    path('history/', views.conversion_history, name='conversion_history'),
    path('history/<int:record_id>/', views.record_detail, name='record_detail'),
    path('history/<int:record_id>/delete/', views.delete_record, name='delete_record'),
    path('history/bulk-delete/', views.bulk_delete_records, name='bulk_delete_records'),
    path('history/export/', views.export_records, name='export_records'),
    path('history/statistics/', views.statistics_data, name='statistics_data'),
    path('result/<int:image_id>/<int:result_index>/', views.result_detail, name='result_detail'),
]