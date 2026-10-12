from rest_framework import serializers
from .models import Scan, Diagnosis
from storage.service import get_signed_url

class DiagnosisSerializer(serializers.ModelSerializer):
    heatmap_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Diagnosis
        fields = ['model_confidence', 'detection_result', 'gradcam_image_path', 'heatmap_image_url', 'radiologist_notes', 'created_at']

    def get_heatmap_image_url(self, obj):
        if obj.gradcam_image_path:
            return f"/api/diagnostics/scans/{obj.scan_id}/heatmap/"
        return None

class ScanSerializer(serializers.ModelSerializer):
    diagnosis = DiagnosisSerializer(read_only=True)
    patient_name = serializers.CharField(source='patient.name', read_only=True)
    patient_id_code = serializers.CharField(source='patient.patient_id', read_only=True)
    original_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Scan
        fields = [
            'id', 'patient', 'patient_name', 'patient_id_code', 
            'uploaded_by', 'image_path', 'original_filename', 
            'original_image_url',
            'file_type', 'file_size', 'upload_timestamp', 'diagnosis'
        ]

    def get_original_image_url(self, obj):
        if obj.image_path:
            return f"/api/diagnostics/scans/{obj.id}/image/"
        return None
