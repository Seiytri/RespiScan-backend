from django.urls import path
from .views import CSRFTokenView, SignupView, LoginView, LogoutView, UserMeView

urlpatterns = [
    path('csrf/', CSRFTokenView.as_view(), name='csrf'),
    path('signup/', SignupView.as_view(), name='signup'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('me/', UserMeView.as_view(), name='user-me'),
]
