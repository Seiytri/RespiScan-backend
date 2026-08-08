from django.urls import path
from .views import (
    CSRFTokenView,
    SignupView,
    LoginView,
    LogoutView,
    UserMeView,
    TOTPSetupView,
    TOTPConfirmView,
)

urlpatterns = [
    path('csrf/', CSRFTokenView.as_view(), name='csrf'),
    path('signup/', SignupView.as_view(), name='signup'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('me/', UserMeView.as_view(), name='user-me'),

    # TOTP two-factor authentication
    path('totp/setup/', TOTPSetupView.as_view(), name='totp-setup'),
    path('totp/confirm/', TOTPConfirmView.as_view(), name='totp-confirm'),
]
