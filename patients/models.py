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
    
    # Extended Demographics
    civil_status = models.CharField(max_length=50, blank=True, null=True)
    nationality = models.CharField(max_length=50, blank=True, null=True, default='Filipino')
    occupation = models.CharField(max_length=100, blank=True, null=True)
    philhealth_number = models.CharField(max_length=50, blank=True, null=True)
    
    # Contact
    contact_number = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    residential_address = models.TextField(blank=True, null=True)
    
    # Emergency
    emergency_contact_name = models.CharField(max_length=255, blank=True, null=True)
    emergency_contact_relationship = models.CharField(max_length=50, blank=True, null=True)
    emergency_contact_number = models.CharField(max_length=20, blank=True, null=True)
    
    # Clinical
    chief_complaint = models.TextField(blank=True, null=True)
    medical_history = models.JSONField(default=list, blank=True, null=True)
    allergies = models.CharField(max_length=255, blank=True, null=True)
    current_medications = models.TextField(blank=True, null=True)
    smoking_status = models.CharField(max_length=50, blank=True, null=True)
    referring_physician = models.CharField(max_length=255, blank=True, null=True)
    
    # System
    last_scan_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.patient_id})"
