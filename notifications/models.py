from django.db import models
from django.conf import settings

class NotificationPreference(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notification_preferences')
    
    # Channels
    email_enabled = models.BooleanField(default=True)
    in_app_enabled = models.BooleanField(default=True)
    
    # Events
    on_diagnosis_ready = models.BooleanField(default=True)
    on_positive_detection = models.BooleanField(default=True)
    on_new_patient = models.BooleanField(default=False)
    on_report_generated = models.BooleanField(default=True)
    on_employee_activity = models.BooleanField(default=False, help_text="Admin only: sign-in activity")
    on_system_alerts = models.BooleanField(default=True, help_text="Admin only: system/model alerts")

    def __str__(self):
        return f"Prefs for {self.user.username}"
