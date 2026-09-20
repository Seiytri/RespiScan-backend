from rest_framework import serializers
from .models import Patient

class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = [
            'id', 'patient_id', 'name', 'age', 'gender', 'contact_number', 
            'emergency_contact_name', 'emergency_contact_relationship', 'emergency_contact_number',
            'last_scan_date', 'status', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_scan_date', 'status']
