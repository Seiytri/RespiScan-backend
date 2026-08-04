from django.db import models

STATUS_CHOICES = (
    ('Positive', 'Positive'),
    ('Negative', 'Negative'),
    ('Pending', 'Pending'),
)

class Patient(models.Model):
    patient_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    age = models.PositiveIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=20, blank=True)
    last_scan_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.patient_id})"
