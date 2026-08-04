from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Patient
from .serializers import PatientSerializer

class PatientViewSet(viewsets.ModelViewSet):
    queryset = Patient.objects.all().order_by('created_at')
    serializer_class = PatientSerializer
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    # Filter by exact fields
    filterset_fields = ['status', 'gender']
    
    # Search by partial match on these fields
    search_fields = ['name', 'patient_id']
    
    # Allow frontend to order by these fields
    ordering_fields = ['created_at', 'last_scan_date', 'name', 'age']
    ordering = ['-created_at']
