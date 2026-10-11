from celery import shared_task
import uuid
import requests

from django.db import transaction
from diagnostics.models import Scan, Diagnosis
from inference.service import run_inference
from storage.service import upload_file, get_signed_url

@shared_task
def process_scan_task(scan_id: int):
    """
    Asynchronous task to process an uploaded scan.
    
    1. Downloads the image from Supabase.
    2. Runs inference.
    3. Uploads the Grad-CAM heatmap back to Supabase.
    4. Updates the Diagnosis model.
    """
    try:
        scan = Scan.objects.select_related('patient', 'diagnosis').get(id=scan_id)
        diagnosis = scan.diagnosis
    except (Scan.DoesNotExist, Diagnosis.DoesNotExist):
        return

    # 1. Download the original image from Supabase (using a signed URL to fetch it securely)
    signed_url = get_signed_url(bucket="respiscan-scans", path=scan.image_path)
    if not signed_url:
        return
        
    response = requests.get(signed_url, timeout=30)
    response.raise_for_status()
    image_bytes = response.content

    # 2. Run inference
    try:
        result = run_inference(image_bytes)
    except Exception as e:
        diagnosis.detection_result = 'Failed'
        diagnosis.save()
        return

    # 3. Upload Grad-CAM heatmap if present
    gradcam_path = ""
    if result.get("gradcam_image"):
        heatmap_bytes = result["gradcam_image"]
        # Generate a unique path for the heatmap
        gradcam_path = f"{scan.image_path}_heatmap_{uuid.uuid4().hex}.png"
        upload_file(
            bucket="respiscan-scans",
            path=gradcam_path,
            file_data=heatmap_bytes,
            content_type="image/png"
        )

    # 4. Update Diagnosis
    raw_prediction = result.get("prediction", "Pending")
    if raw_prediction == "Normal":
        mapped_result = "Negative"
    elif raw_prediction == "Pending":
        mapped_result = "Pending"
    else:
        mapped_result = "Positive"

    with transaction.atomic():
        diagnosis.detection_result = mapped_result
        diagnosis.model_confidence = result.get("confidence", 0.0)
        diagnosis.gradcam_image_path = gradcam_path
        diagnosis.save()

        # Update patient latest scan info only if this scan is newer or equal (avoid out-of-order race conditions)
        patient = scan.patient
        if patient:
            is_newer = (patient.last_scan_date is None) or (scan.upload_timestamp >= patient.last_scan_date)
            if is_newer:
                patient.last_scan_date = scan.upload_timestamp
                if mapped_result in ['Positive', 'Negative']:
                    patient.status = mapped_result
                patient.save(update_fields=['last_scan_date', 'status', 'updated_at'])
        
    # (Optional) We could trigger a notification here using notifications.service.send_email
