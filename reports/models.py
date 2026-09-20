from django.db import models
from django.conf import settings
from diagnostics.models import Diagnosis


class Report(models.Model):
    REPORT_TYPES = (
        ('system', 'System Report'),
        ('clinical', 'Clinical Report'),
        ('analytics', 'Analytics Export'),
    )

    diagnosis = models.ForeignKey(
        Diagnosis, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='reports',
    )
    title = models.CharField(max_length=255)
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    file_path = models.CharField(
        max_length=512, blank=True,
        help_text="Path to report file in Supabase or local storage",
    )

    # Date range for analytics reports (from thesis ERD)
    date_range_start = models.DateField(null=True, blank=True)
    date_range_end = models.DateField(null=True, blank=True)

    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='generated_reports',
    )
    generated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
