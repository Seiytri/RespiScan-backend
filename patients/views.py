from rest_framework import viewsets, filters, pagination
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as django_filters
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

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()
