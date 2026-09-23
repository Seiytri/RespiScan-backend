from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Administrator'),
        ('employee', 'Employee'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='employee')
    title = models.CharField(max_length=100, blank=True, help_text="e.g., Radiologic Technologist, Pulmonologist")
    department = models.CharField(max_length=100, blank=True)
    license_number = models.CharField(max_length=50, blank=True, help_text="PRC License Number")
    bio = models.TextField(blank=True)

    def __str__(self):
        return self.username

    @property
    def is_admin(self):
        return self.role == 'admin' or self.is_superuser
