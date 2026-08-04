from django.db import models

class SystemSettings(models.Model):
    """
    Singleton model for system-wide configuration.
    """
    confidence_threshold = models.FloatField(default=0.85, help_text="AI confidence threshold for positive detection")
    gradcam_overlay_default = models.BooleanField(default=True, help_text="Show Grad-CAM overlay by default")
    auto_generate_report = models.BooleanField(default=True)
    data_retention_period = models.PositiveIntegerField(default=365, help_text="Days to retain data")
    audit_logging_enabled = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        # Ensure only one record exists
        if not self.pk and SystemSettings.objects.exists():
            return
        super().save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "System Settings"
