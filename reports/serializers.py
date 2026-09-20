from rest_framework import serializers
from .models import Report


class ReportSerializer(serializers.ModelSerializer):
    generated_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = [
            'id', 'title', 'report_type', 'file_path',
            'date_range_start', 'date_range_end',
            'generated_by', 'generated_by_name', 'generated_at',
        ]
        read_only_fields = ['id', 'generated_at', 'generated_by', 'generated_by_name']

    def get_generated_by_name(self, obj):
        if obj.generated_by:
            u = obj.generated_by
            name = f"{u.first_name} {u.last_name}".strip()
            return name or u.username
        return "System"
