from django.urls import path
from .views import AnalyticsView

urlpatterns = [
    path('dashboard/', AnalyticsView.as_view(), name='analytics-dashboard'),
]
