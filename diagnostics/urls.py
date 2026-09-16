from django.urls import path
from .views import ScanUploadView

urlpatterns = [
    path('upload/', ScanUploadView.as_view(), name='scan-upload'),
]
