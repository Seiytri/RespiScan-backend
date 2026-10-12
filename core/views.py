from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from patients.models import Patient
from diagnostics.models import Scan, Diagnosis
from reports.models import Report
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta

class AnalyticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        now = timezone.now()

        # ── Optional filters from query params ──────────────────────
        gender = request.query_params.get('gender', '').strip()
        age_min = request.query_params.get('age_min')
        age_max = request.query_params.get('age_max')

        # Build patient filter
        patient_q = Q(is_active=True)
        if gender:
            patient_q &= Q(gender__iexact=gender)
        if age_min:
            patient_q &= Q(age__gte=int(age_min))
        if age_max:
            patient_q &= Q(age__lte=int(age_max))

        filtered_patients = Patient.objects.filter(patient_q)
        filtered_patient_ids = filtered_patients.values_list('id', flat=True)

        # Build scan/diagnosis filters based on filtered patients
        filtered_scans = Scan.objects.filter(patient_id__in=filtered_patient_ids)
        filtered_diagnoses = Diagnosis.objects.filter(scan__patient_id__in=filtered_patient_ids)

        total_patients = filtered_patients.count()
        total_scans = filtered_scans.count()
        positive_detections = filtered_diagnoses.filter(detection_result='Positive').count()
        reports_generated = Report.objects.count()

        # ── Week-over-week growth ───────────────────────────────────
        seven_days_ago = now - timedelta(days=7)
        fourteen_days_ago = now - timedelta(days=14)
        
        scans_this_week = filtered_scans.filter(upload_timestamp__gte=seven_days_ago).count()
        scans_last_week = filtered_scans.filter(upload_timestamp__gte=fourteen_days_ago, upload_timestamp__lt=seven_days_ago).count()
        
        if scans_last_week > 0:
            growth = ((scans_this_week - scans_last_week) / scans_last_week) * 100
            scan_growth_percent = round(growth, 1)
        elif scans_this_week > 0:
            scan_growth_percent = 100.0
        else:
            scan_growth_percent = 0.0

        # ── Weekly activity ─────────────────────────────────────────
        weekly_activity = []
        for i in range(7):
            day = now - timedelta(days=6 - i)
            scans = filtered_scans.filter(upload_timestamp__date=day.date()).count()
            positive = filtered_diagnoses.filter(
                scan__upload_timestamp__date=day.date(),
                detection_result='Positive'
            ).count()
            weekly_activity.append({
                'name': day.strftime('%a'),
                'scans': scans,
                'positive': positive
            })

        # ── Monthly trends ──────────────────────────────────────────
        monthly_trends = []
        highest_volume_month = {'name': None, 'scans': 0}
        for i in range(6):
            month_date = now - timedelta(days=30 * (5 - i))
            scans = filtered_scans.filter(
                upload_timestamp__year=month_date.year,
                upload_timestamp__month=month_date.month
            ).count()
            positive = filtered_diagnoses.filter(
                scan__upload_timestamp__year=month_date.year,
                scan__upload_timestamp__month=month_date.month,
                detection_result='Positive'
            ).count()
            
            pos_rate = round((positive / scans * 100), 1) if scans > 0 else 0.0
            
            monthly_trends.append({
                'name': month_date.strftime('%b'),
                'Scans': scans,
                'Positive': positive,
                'positivity_rate': pos_rate
            })
            if scans > highest_volume_month['scans']:
                highest_volume_month = {'name': month_date.strftime('%B'), 'scans': scans}

        # ── Distribution (pos vs neg) ───────────────────────────────
        negative_detections = filtered_diagnoses.filter(detection_result='Negative').count()
        distribution = [
            {'name': 'Positive', 'value': positive_detections, 'color': '#ef4444'},
            {'name': 'Negative', 'value': negative_detections, 'color': '#0ea5e9'}
        ]

        # ── Gender distribution ─────────────────────────────────────
        male_count = filtered_patients.filter(gender__iexact='Male').count()
        female_count = filtered_patients.filter(gender__iexact='Female').count()
        gender_distribution = [
            {'name': 'Male', 'value': male_count},
            {'name': 'Female', 'value': female_count},
        ]

        # ── Age-range pneumonia breakdown & Age+Gender ──────────────
        AGE_BUCKETS = [
            ('0-5', 0, 5),
            ('6-12', 6, 12),
            ('13-17', 13, 17),
            ('18-30', 18, 30),
            ('31-45', 31, 45),
            ('46-60', 46, 60),
            ('61+', 61, 200),
        ]
        age_pneumonia = []
        age_gender_distribution = []
        highest_risk = {'group': None, 'rate': 0}

        for label, lo, hi in AGE_BUCKETS:
            bucket_patients = filtered_patients.filter(age__gte=lo, age__lte=hi)
            
            male_bucket_ids = bucket_patients.filter(gender__iexact='Male').values_list('id', flat=True)
            female_bucket_ids = bucket_patients.filter(gender__iexact='Female').values_list('id', flat=True)
            
            male_pos = filtered_diagnoses.filter(scan__patient_id__in=male_bucket_ids, detection_result='Positive').count()
            female_pos = filtered_diagnoses.filter(scan__patient_id__in=female_bucket_ids, detection_result='Positive').count()
            total_pos = male_pos + female_pos
            total = bucket_patients.count()
            
            if total > 0:
                rate = (total_pos / total) * 100
                if rate > highest_risk['rate']:
                    highest_risk = {'group': label, 'rate': rate, 'pos': total_pos, 'total': total}

            age_pneumonia.append({
                'range': label,
                'positive': total_pos,
                'total': total,
            })
            
            age_gender_distribution.append({
                'range': label,
                'Male': male_pos,
                'Female': female_pos,
            })

        # ── Recent activity ─────────────────────────────────────────
        recent_diagnoses = filtered_diagnoses.select_related('scan__patient').order_by('-created_at')[:5]
        recent_activity = []
        for d in recent_diagnoses:
            mins_ago = int((now - d.created_at).total_seconds() / 60)
            patient = getattr(d.scan, 'patient', None) if hasattr(d, 'scan') else None
            patient_code = patient.patient_id if patient else 'N/A'
            patient_name = patient.name if patient else 'Unknown Patient'
            patient_pk = patient.id if patient else None
            gender = patient.gender if patient else ''
            age = patient.age if patient else None
            recent_activity.append({
                'action': 'Diagnosis Completed',
                'patient_id': patient_code,
                'patient_name': patient_name,
                'patient_pk': patient_pk,
                'gender': gender,
                'age': age,
                'detection_result': d.detection_result,
                'minutes_ago': mins_ago
            })
            
        # ── Key Findings ────────────────────────────────────────────
        key_findings = []
        
        # 1. Growth Alert
        if scan_growth_percent > 0:
            key_findings.append({
                'id': 'growth', 'icon': 'TrendingUp', 'type': 'neutral', 'title': 'Increasing Scan Volume', 
                'description': f'Scans processed increased by {scan_growth_percent}% compared to last week.'
            })
        elif scan_growth_percent < 0:
            key_findings.append({
                'id': 'growth', 'icon': 'TrendingDown', 'type': 'success', 'title': 'Decreasing Scan Volume', 
                'description': f'Scans processed dropped by {abs(scan_growth_percent)}% compared to last week.'
            })
            
        # 2. Risk Demographic
        if highest_risk['group']:
            key_findings.append({
                'id': 'risk', 'icon': 'AlertTriangle', 'type': 'warning', 'title': 'Highest Risk Demographic',
                'description': f'Patients aged {highest_risk["group"]} have the highest positivity rate ({round(highest_risk["rate"])}%).'
            })
            
        # 3. Peak Month
        if highest_volume_month['name']:
            key_findings.append({
                'id': 'peak', 'icon': 'Info', 'type': 'info', 'title': 'Peak Detection Month',
                'description': f'{highest_volume_month["name"]} had the highest volume of scans ({highest_volume_month["scans"]} scans).'
            })

        return Response({
            'total_patients': total_patients,
            'total_scans': total_scans,
            'positive_detections': positive_detections,
            'reports_generated': reports_generated,
            'scan_growth_percent': scan_growth_percent,
            'weekly_activity': weekly_activity,
            'monthly_trends': monthly_trends,
            'distribution': distribution,
            'gender_distribution': gender_distribution,
            'age_pneumonia': age_pneumonia,
            'age_gender_distribution': age_gender_distribution,
            'recent_activity': recent_activity,
            'key_findings': key_findings,
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
