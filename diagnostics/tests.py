from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch, MagicMock

from patients.models import Patient
from .models import Scan, Diagnosis
from .tasks import process_scan_task

User = get_user_model()

class ScanUploadTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', 
            password='testpassword'
        )
        self.patient = Patient.objects.create(
            patient_id='P123',
            name='John Doe',
            age=30,
            gender='Male'
        )
        self.client.login(username='testuser', password='testpassword')
        self.url = reverse('scan-upload') if hasattr(reverse, 'scan-upload') else '/api/diagnostics/upload/' # Fallback if name is not scan-upload

    @patch('diagnostics.views.process_scan_task.delay')
    @patch('diagnostics.views.upload_file')
    def test_scan_upload_endpoint(self, mock_upload_file, mock_task_delay):
        # 1. Test the Upload Endpoint
        image_content = b"fake_image_data"
        file = SimpleUploadedFile("test_scan.png", image_content, content_type="image/png")
        
        response = self.client.post(
            self.url,
            {'file': file, 'patient_id': self.patient.id},
            format='multipart'
        )
        
        self.assertEqual(response.status_code, 202)
        self.assertIn('scan_id', response.data)
        
        scan_id = response.data['scan_id']
        scan = Scan.objects.get(id=scan_id)
        
        # Verify db records
        self.assertEqual(scan.original_filename, "test_scan.png")
        self.assertTrue(hasattr(scan, 'diagnosis'))
        self.assertEqual(scan.diagnosis.detection_result, 'Pending')
        
        # Verify mocks
        mock_upload_file.assert_called_once()
        mock_task_delay.assert_called_once_with(scan_id)

    @patch('diagnostics.tasks.get_signed_url')
    @patch('diagnostics.tasks.requests.get')
    @patch('diagnostics.tasks.run_inference')
    @patch('diagnostics.tasks.upload_file')
    def test_process_scan_task(self, mock_upload_file, mock_run_inference, mock_requests_get, mock_get_signed_url):
        # Setup mock db state
        scan = Scan.objects.create(
            patient=self.patient,
            uploaded_by=self.user,
            image_path='scans/1/fake.png',
            original_filename='fake.png',
            file_type='image/png',
            file_size=123
        )
        Diagnosis.objects.create(scan=scan, detection_result='Pending', created_by=self.user)

        # Setup mock returns
        mock_get_signed_url.return_value = "http://fake-signed-url.com/fake.png"
        
        mock_response = MagicMock()
        mock_response.content = b"downloaded_image_bytes"
        mock_response.raise_for_status = MagicMock()
        mock_requests_get.return_value = mock_response

        mock_run_inference.return_value = {
            "prediction": "Positive",
            "confidence": 0.95,
            "gradcam_image": b"fake_heatmap_bytes"
        }

        # 2. Test the Task
        process_scan_task(scan.id)
        
        # Refresh from db
        scan.refresh_from_db()
        diagnosis = scan.diagnosis
        
        self.assertEqual(diagnosis.detection_result, 'Positive')
        self.assertEqual(diagnosis.model_confidence, 0.95)
        self.assertTrue(diagnosis.gradcam_image_path.startswith(scan.image_path + '_heatmap_'))
        
        mock_get_signed_url.assert_called_once_with(bucket="respiscan-scans", path=scan.image_path)
        mock_requests_get.assert_called_once_with("http://fake-signed-url.com/fake.png")
        mock_run_inference.assert_called_once_with(b"downloaded_image_bytes")
        mock_upload_file.assert_called_once()
        
        # Verify heatmap upload args
        args, kwargs = mock_upload_file.call_args
        self.assertEqual(kwargs['bucket'], "respiscan-scans")
        self.assertEqual(kwargs['file_data'], b"fake_heatmap_bytes")
        self.assertEqual(kwargs['content_type'], "image/png")

    @patch('diagnostics.views.get_signed_url')
    def test_scan_result_endpoint(self, mock_get_signed_url):
        # Setup mock db state
        scan = Scan.objects.create(
            patient=self.patient,
            uploaded_by=self.user,
            image_path='scans/1/fake.png',
            original_filename='fake.png',
            file_type='image/png',
            file_size=123
        )
        Diagnosis.objects.create(
            scan=scan, 
            detection_result='Positive', 
            model_confidence=0.98,
            gradcam_image_path='scans/1/fake_heatmap.png',
            created_by=self.user
        )

        mock_get_signed_url.side_effect = [
            "http://fake-signed-url.com/fake.png",
            "http://fake-signed-url.com/fake_heatmap.png"
        ]

        url = reverse('scan-result', kwargs={'scan_id': scan.id}) if hasattr(reverse, 'scan-result') else f'/api/diagnostics/{scan.id}/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['scan_id'], scan.id)
        self.assertEqual(response.data['status'], 'Positive')
        self.assertEqual(response.data['confidence'], 0.98)
        self.assertEqual(response.data['original_image_url'], "http://fake-signed-url.com/fake.png")
        self.assertEqual(response.data['heatmap_image_url'], "http://fake-signed-url.com/fake_heatmap.png")
        
        # Verify get_signed_url was called correctly
        self.assertEqual(mock_get_signed_url.call_count, 2)
        mock_get_signed_url.assert_any_call("respiscan-scans", scan.image_path)
        mock_get_signed_url.assert_any_call("respiscan-scans", 'scans/1/fake_heatmap.png')

