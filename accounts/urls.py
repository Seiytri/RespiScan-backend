from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CSRFTokenView,
    SignupView,
    LoginView,
    LogoutView,
    UserMeView,
    ChangePasswordView,
    TOTPSetupView,
    TOTPConfirmView,
    EmployeeViewSet,
)

router = DefaultRouter()
router.register(r'employees', EmployeeViewSet, basename='employee')

urlpatterns = [
    path('csrf/', CSRFTokenView.as_view(), name='csrf'),
    path('signup/', SignupView.as_view(), name='signup'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('me/', UserMeView.as_view(), name='user-me'),
    path('me/password/', ChangePasswordView.as_view(), name='change-password'),

    # TOTP two-factor authentication
    path('totp/setup/', TOTPSetupView.as_view(), name='totp-setup'),
    path('totp/confirm/', TOTPConfirmView.as_view(), name='totp-confirm'),

    # Employee management (admin only)
    path('', include(router.urls)),
]
