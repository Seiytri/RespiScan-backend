from django.urls import path
from .views import (
    ScanUploadView, 
    ScanResultView, 
    ScanExportView, 
    ScanListView,
    ScanImageView,
    ScanHeatmapView,
)

urlpatterns = [
    path('scans/', ScanListView.as_view(), name='scan-list'),
    path('scans/<int:scan_id>/image/', ScanImageView.as_view(), name='scan-image'),
    path('scans/<int:scan_id>/heatmap/', ScanHeatmapView.as_view(), name='scan-heatmap'),
    path('upload/', ScanUploadView.as_view(), name='scan-upload'),
    path('<int:scan_id>/', ScanResultView.as_view(), name='scan-result'),
    path('<int:scan_id>/export/', ScanExportView.as_view(), name='scan-export'),
]
