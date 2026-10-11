from rest_framework import serializers
from .models import Scan, Diagnosis

class DiagnosisSerializer(serializers.ModelSerializer):
    class Meta:
        model = Diagnosis
        fields = ['model_confidence', 'detection_result', 'gradcam_image_path', 'radiologist_notes', 'created_at']

class ScanSerializer(serializers.ModelSerializer):
    diagnosis = DiagnosisSerializer(read_only=True)
    patient_name = serializers.CharField(source='patient.name', read_only=True)
    patient_id_code = serializers.CharField(source='patient.patient_id', read_only=True)

    class Meta:
        model = Scan
        fields = [
            'id', 'patient', 'patient_name', 'patient_id_code', 
            'uploaded_by', 'image_path', 'original_filename', 
            'file_type', 'file_size', 'upload_timestamp', 'diagnosis'
        ]
