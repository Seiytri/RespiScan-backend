from django.urls import path
from .views import ScanUploadView, ScanResultView, ScanExportView, ScanListView

urlpatterns = [
    path('scans/', ScanListView.as_view(), name='scan-list'),
    path('upload/', ScanUploadView.as_view(), name='scan-upload'),
    path('<int:scan_id>/', ScanResultView.as_view(), name='scan-result'),
    path('<int:scan_id>/export/', ScanExportView.as_view(), name='scan-export'),
]
