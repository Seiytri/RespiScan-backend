from rest_framework import viewsets, filters, status, pagination
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as django_filters
from storage.service import get_signed_url
from audit.service import log_action
from .models import Patient
from .serializers import PatientSerializer

class StandardResultsSetPagination(pagination.PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100

class PatientFilter(django_filters.FilterSet):
    age_min = django_filters.NumberFilter(field_name="age", lookup_expr='gte')
    age_max = django_filters.NumberFilter(field_name="age", lookup_expr='lte')

    class Meta:
        model = Patient
        fields = ['status', 'gender']

class PatientViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Patient.objects.filter(is_active=True).order_by('-created_at')
    serializer_class = PatientSerializer
    pagination_class = StandardResultsSetPagination
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    # Filter by exact fields
    filterset_class = PatientFilter
    
    # Search by partial match on these fields
    search_fields = ['name', 'patient_id']
    
    # Allow frontend to order by these fields
    ordering_fields = ['created_at', 'last_scan_date', 'name', 'age']
    ordering = ['-created_at']

    def get_object(self):
        """
        Support looking up patient by either numeric primary key (id)
        or clinical alphanumeric string identifier (patient_id).
        """
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup_val = self.kwargs.get(lookup_url_kwarg)
        if lookup_val is not None:
            if str(lookup_val).isdigit():
                obj = Patient.objects.filter(id=lookup_val, is_active=True).first()
                if not obj:
                    obj = Patient.objects.filter(patient_id=lookup_val, is_active=True).first()
            else:
                obj = Patient.objects.filter(patient_id=lookup_val, is_active=True).first()
            if obj:
                self.check_object_permissions(self.request, obj)
                return obj
            raise NotFound("Patient not found.")
        return super().get_object()

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()

    @action(detail=True, methods=['get'], url_path='history')
    def history(self, request, pk=None):
        """
        Retrieve complete historical scans and diagnoses for a patient.
        Returns both original CXR and Grad-CAM heatmap signed URLs for each scan,
        ordered chronologically (most recent first). Supports ?limit= and ?offset= query params.
        """
        patient = self.get_object()

        # Support pagination / limit to prevent DoS via unbounded signed URL loops
        try:
            limit = int(request.query_params.get('limit', 50))
            offset = int(request.query_params.get('offset', 0))
        except (ValueError, TypeError):
            limit = 50
            offset = 0

        limit = max(1, min(limit, 100))
        offset = max(0, offset)

        scans_qs = patient.scans.select_related('diagnosis', 'uploaded_by').order_by('-upload_timestamp')
        total_count = scans_qs.count()
        scans = scans_qs[offset:offset + limit]

        history_data = []
        for scan in scans:
            diag = getattr(scan, 'diagnosis', None)
            
            # Generate temporary secure signed URLs (5 min TTL) with defensive exception handling
            original_url = None
            if scan.image_path:
                try:
                    url = get_signed_url("respiscan-scans", scan.image_path, expires_in=300)
                    original_url = url if url else None
                except Exception:
                    original_url = None

            heatmap_url = None
            if diag and diag.gradcam_image_path:
                try:
                    url = get_signed_url("respiscan-scans", diag.gradcam_image_path, expires_in=300)
                    heatmap_url = url if url else None
                except Exception:
                    heatmap_url = None

            history_data.append({
                "scan_id": scan.id,
                "upload_timestamp": scan.upload_timestamp.isoformat() if scan.upload_timestamp else None,
                "original_filename": scan.original_filename,
                "file_size": scan.file_size,
                "uploaded_by": scan.uploaded_by.username if scan.uploaded_by else None,
                "original_image_url": original_url,
                "heatmap_image_url": heatmap_url,
                "status": diag.detection_result if diag else "Pending",
                "confidence": diag.model_confidence if diag else None,
                "radiologist_notes": diag.radiologist_notes if diag else "",
                "diagnosis_date": diag.created_at.isoformat() if diag and diag.created_at else None,
            })

        # Capture client IP and User-Agent for HIPAA audit trail compliance
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        client_ip = x_forwarded_for.split(',')[0].strip() if x_forwarded_for else request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:255]

        log_action(
            user=request.user,
            action="patient_history_viewed",
            target_object=f"Patient:{patient.id}",
            metadata={
                "patient_id": patient.patient_id,
                "scan_count": len(history_data),
                "total_scans": total_count,
                "ip_address": client_ip,
                "user_agent": user_agent,
            }
        )

        response = Response({
            "patient_id": patient.patient_id,
            "name": patient.name,
            "total_scans": total_count,
            "limit": limit,
            "offset": offset,
            "scans": history_data
        }, status=status.HTTP_200_OK)
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
        return response
