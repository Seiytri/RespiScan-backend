from django.contrib import admin
from .models import Patient

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('patient_id', 'name', 'status', 'is_active', 'created_at')
    list_filter = ('status', 'is_active', 'gender')
    search_fields = ('name', 'patient_id')
