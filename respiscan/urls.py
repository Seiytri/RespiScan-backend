from django.contrib import admin
from django.urls import path, include

api_urlpatterns = [
    path('auth/', include('accounts.urls')),
    path('patients/', include('patients.urls')),
    path('diagnostics/', include('diagnostics.urls')),
    # path('reports/', include('reports.urls')),
    # path('settings/', include('core.urls')),
]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(api_urlpatterns)),
]

