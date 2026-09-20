from datetime import date, timedelta
from django.http import HttpResponse
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Report
from .serializers import ReportSerializer
from .services import generate_analytics_pdf


class ReportListView(APIView):
    """List all previously generated reports."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        reports = Report.objects.all().order_by('-generated_at')[:50]
        serializer = ReportSerializer(reports, many=True)
        return Response(serializer.data)


class ReportGenerateView(APIView):
    """
    Generate an analytics PDF report for a date range.
    POST body (optional):
      - date_range_start: YYYY-MM-DD (defaults to 30 days ago)
      - date_range_end:   YYYY-MM-DD (defaults to today)
    Returns the PDF as a downloadable file and saves a Report record.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        today = date.today()
        start_str = request.data.get('date_range_start')
        end_str = request.data.get('date_range_end')

        try:
            start_date = date.fromisoformat(start_str) if start_str else today - timedelta(days=30)
            end_date = date.fromisoformat(end_str) if end_str else today
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Generate the PDF bytes
        pdf_bytes = generate_analytics_pdf(start_date, end_date)

        # Save a Report record in the database
        title = f"Analytics Report — {start_date.strftime('%b %d')} to {end_date.strftime('%b %d, %Y')}"
        report = Report.objects.create(
            title=title,
            report_type='analytics',
            date_range_start=start_date,
            date_range_end=end_date,
            generated_by=request.user,
            file_path=f"reports/analytics_{start_date}_{end_date}.pdf",
        )

        # Return the PDF as a downloadable response
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="respiscan_analytics_{start_date}_{end_date}.pdf"'
        return response
