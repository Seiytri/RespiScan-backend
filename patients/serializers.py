from rest_framework import serializers
from .models import Patient

class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = [
            'id', 'patient_id', 'name', 'age', 'gender', 'contact_number', 
            'civil_status', 'nationality', 'occupation', 'philhealth_number',
            'email', 'residential_address',
            'emergency_contact_name', 'emergency_contact_relationship', 'emergency_contact_number',
            'chief_complaint', 'medical_history', 'allergies', 'current_medications',
            'smoking_status', 'referring_physician',
            'last_scan_date', 'status', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_scan_date', 'status']
