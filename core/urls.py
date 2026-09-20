from django.urls import path
from .views import AnalyticsView, SystemSettingsView

urlpatterns = [
    path('dashboard/', AnalyticsView.as_view(), name='analytics-dashboard'),
    path('system-settings/', SystemSettingsView.as_view(), name='system-settings'),
]
