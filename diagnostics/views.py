from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser
import uuid

from .models import Scan, Diagnosis
from storage.service import upload_file
from .tasks import process_scan_task
from audit.service import log_action

class ScanUploadView(views.APIView):
    """
    Handles chest X-ray uploads.
    Saves the file to Supabase, creates the database records,
    and dispatches a Celery task to run the inference model asynchronously.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request):
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)
            
        patient_id = request.data.get('patient_id')
        if not patient_id:
            return Response({"error": "patient_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Generate a unique path for Supabase
        ext = file_obj.name.split('.')[-1]
        unique_filename = f"{uuid.uuid4().hex}.{ext}"
        storage_path = f"scans/{patient_id}/{unique_filename}"

        # 1. Upload original file to Supabase
        upload_file(
            bucket="respiscan-scans",
            path=storage_path,
            file_data=file_obj.read(),
            content_type=file_obj.content_type
        )

        # 2. Create Database Records
        scan = Scan.objects.create(
            patient_id=patient_id,
            uploaded_by=request.user,
            image_path=storage_path,
            original_filename=file_obj.name,
            file_type=file_obj.content_type,
            file_size=file_obj.size
        )
        
        Diagnosis.objects.create(
            scan=scan,
            detection_result='Pending',
            created_by=request.user
        )
        
        # Log the sensitive action
        log_action(
            user=request.user,
            action="scan_uploaded",
            target_object=f"Scan:{scan.id}",
            metadata={"patient_id": patient_id}
        )

        # 3. Trigger Async Celery Task
        process_scan_task.delay(scan.id)

        return Response({
            "message": "Scan uploaded successfully. Inference is running in the background.",
            "scan_id": scan.id
        }, status=status.HTTP_202_ACCEPTED)

from storage.service import get_signed_url

class ScanResultView(views.APIView):
    """
    Fetches the status and results of a scan diagnosis.
    Returns signed URLs for the images if they exist.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, scan_id):
        try:
            scan = Scan.objects.get(id=scan_id)
            diagnosis = scan.diagnosis
        except (Scan.DoesNotExist, Diagnosis.DoesNotExist):
            return Response({"error": "Scan not found"}, status=status.HTTP_404_NOT_FOUND)

        # Get signed urls for frontend display
        original_url = get_signed_url("respiscan-scans", scan.image_path) if scan.image_path else None
        heatmap_url = get_signed_url("respiscan-scans", diagnosis.gradcam_image_path) if diagnosis.gradcam_image_path else None

        return Response({
            "scan_id": scan.id,
            "status": diagnosis.detection_result,
            "confidence": diagnosis.model_confidence,
            "original_image_url": original_url,
            "heatmap_image_url": heatmap_url,
            "radiologist_notes": diagnosis.radiologist_notes
        })

from django.http import HttpResponse
from reports.services import generate_clinical_pdf

class ScanExportView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, scan_id):
        try:
            pdf_bytes = generate_clinical_pdf(scan_id)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
            
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="scan_{scan_id}_report.pdf"'
        return response
