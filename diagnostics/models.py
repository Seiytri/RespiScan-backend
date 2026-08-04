from django.db import models
from django.conf import settings
from patients.models import Patient

class Scan(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='scans')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='uploaded_scans')
    image_path = models.CharField(max_length=512, help_text="Path in Supabase Storage")
    original_filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=50)
    file_size = models.PositiveIntegerField(help_text="Size in bytes")
    upload_timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Scan {self.id} for {self.patient.name}"

class Diagnosis(models.Model):
    RESULT_CHOICES = (
        ('Positive', 'Positive'),
        ('Negative', 'Negative'),
        ('Pending', 'Pending'),
    )

    scan = models.OneToOneField(Scan, on_delete=models.CASCADE, related_name='diagnosis')
    model_confidence = models.FloatField(null=True, blank=True)
    detection_result = models.CharField(max_length=20, choices=RESULT_CHOICES, default='Pending')
    gradcam_image_path = models.CharField(max_length=512, blank=True, help_text="Path to Grad-CAM heatmap in Supabase")
    radiologist_notes = models.TextField(blank=True)
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_diagnoses')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Diagnosis for Scan {self.scan.id}"
