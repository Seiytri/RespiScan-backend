import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from diagnostics.models import Scan

def generate_clinical_pdf(scan_id: int) -> bytes:
    scan = Scan.objects.select_related('patient', 'diagnosis').get(id=scan_id)
    patient = scan.patient
    diagnosis = scan.diagnosis
    
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, 750, "RespiScan Clinical Report")
    
    p.setFont("Helvetica", 12)
    
    name = patient.name if patient else "N/A"
    pid = patient.patient_id if patient else "N/A"
    age = patient.age if patient else "N/A"
    gender = patient.gender if patient else "N/A"
    
    p.drawString(100, 710, f"Patient Name: {name}")
    p.drawString(100, 690, f"Patient ID: {pid}")
    p.drawString(100, 670, f"Age: {age}")
    p.drawString(100, 650, f"Gender: {gender}")
    
    p.drawString(100, 610, f"Upload Date: {scan.created_at.strftime('%Y-%m-%d %H:%M')}")
    p.drawString(100, 590, f"Filename: {scan.original_filename}")
    
    det_result = diagnosis.detection_result if diagnosis else "N/A"
    conf = diagnosis.model_confidence if diagnosis else "N/A"
    notes = diagnosis.radiologist_notes if diagnosis else ""
    
    p.drawString(100, 550, f"Diagnosis Result: {det_result}")
    p.drawString(100, 530, f"Confidence: {conf}")
    
    if notes:
        p.drawString(100, 490, "Radiologist Notes:")
        p.drawString(100, 470, notes[:80])
        
    p.showPage()
    p.save()
    
    buffer.seek(0)
    return buffer.read()
