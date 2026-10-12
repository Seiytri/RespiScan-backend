from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Administrator'),
        ('employee', 'Employee'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='employee')
    title = models.CharField(max_length=100, blank=True, help_text='e.g., Radiologic Technologist, Pulmonologist')
    department = models.CharField(max_length=100, blank=True)
    license_number = models.CharField(max_length=50, blank=True, help_text='PRC License Number')
    bio = models.TextField(blank=True)
    avatar_path = models.CharField(max_length=512, blank=True, null=True, help_text="Path to avatar image in Supabase Storage")
    avatar_url = models.TextField(blank=True, null=True, help_text="Cached signed URL for avatar image")

    def __str__(self):
        return self.username

    @property
    def is_admin(self):
        return self.role == 'admin' or self.is_superuser

class DeviceSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='device_sessions')
    session_key = models.CharField(max_length=40, unique=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f'{self.user.username} - {self.ip_address}'


from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    if not request.session.session_key:
        request.session.create()
    DeviceSession.objects.update_or_create(
        session_key=request.session.session_key,
        defaults={
            'user': user,
            'ip_address': get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', '')[:255]
        }
    )
