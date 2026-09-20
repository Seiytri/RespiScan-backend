from django.urls import path
from .views import ReportListView, ReportGenerateView

urlpatterns = [
    path('', ReportListView.as_view(), name='report-list'),
    path('generate/', ReportGenerateView.as_view(), name='report-generate'),
]
