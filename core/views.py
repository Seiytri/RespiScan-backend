from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from patients.models import Patient
from diagnostics.models import Scan, Diagnosis
from reports.models import Report
from django.utils import timezone
from datetime import timedelta

class AnalyticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        now = timezone.now()
        
        total_patients = Patient.objects.filter(is_active=True).count()
        total_scans = Scan.objects.count()
        positive_detections = Diagnosis.objects.filter(detection_result='Positive').count()
        reports_generated = Report.objects.count()
        
        weekly_activity = []
        for i in range(7):
            day = now - timedelta(days=6-i)
            scans = Scan.objects.filter(created_at__date=day.date()).count()
            positive = Diagnosis.objects.filter(scan__created_at__date=day.date(), detection_result='Positive').count()
            weekly_activity.append({
                'name': day.strftime('%a'),
                'scans': scans,
                'positive': positive
            })
            
        monthly_trends = []
        for i in range(6):
            month_date = now - timedelta(days=30*(5-i))
            scans = Scan.objects.filter(created_at__year=month_date.year, created_at__month=month_date.month).count()
            positive = Diagnosis.objects.filter(scan__created_at__year=month_date.year, scan__created_at__month=month_date.month, detection_result='Positive').count()
            monthly_trends.append({
                'name': month_date.strftime('%b'),
                'Scans': scans,
                'Positive': positive
            })
            
        negative_detections = Diagnosis.objects.filter(detection_result='Negative').count()
        distribution = [
            {'name': 'Positive', 'value': positive_detections, 'color': '#ef4444'},
            {'name': 'Negative', 'value': negative_detections, 'color': '#0ea5e9'}
        ]
        
        recent_diagnoses = Diagnosis.objects.order_by('-created_at')[:5]
        recent_activity = []
        for d in recent_diagnoses:
            mins_ago = int((now - d.created_at).total_seconds() / 60)
            patient_id = d.scan.patient.patient_id if hasattr(d, 'scan') and hasattr(d.scan, 'patient') else 'N/A'
            recent_activity.append({
                'action': 'Diagnosis Completed',
                'patient_id': patient_id,
                'minutes_ago': mins_ago
            })
            
        return Response({
            'total_patients': total_patients,
            'total_scans': total_scans,
            'positive_detections': positive_detections,
            'reports_generated': reports_generated,
            'weekly_activity': weekly_activity,
            'monthly_trends': monthly_trends,
            'distribution': distribution,
            'recent_activity': recent_activity
        })

from .models import SystemSettings
from rest_framework import serializers
from rest_framework.permissions import IsAdminUser

class SystemSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemSettings
        fields = '__all__'

class SystemSettingsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        settings = SystemSettings.get_settings()
        serializer = SystemSettingsSerializer(settings)
        return Response(serializer.data)

    def patch(self, request):
        settings = SystemSettings.get_settings()
        serializer = SystemSettingsSerializer(settings, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)
