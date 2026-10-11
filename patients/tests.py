from unittest.mock import patch
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from patients.models import Patient
from diagnostics.models import Scan, Diagnosis
from audit.models import AuditLog

User = get_user_model()

class PatientHistoryTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testclinician',
            email='clinician@respiscan.local',
            password='Password123!',
            role='employee',
        )
        self.client.force_authenticate(user=self.user)

        self.patient = Patient.objects.create(
            patient_id='PT-HIST-001',
            name='Elena Gomez',
            age=48,
            gender='Female',
        )

        self.scan1 = Scan.objects.create(
            patient=self.patient,
            uploaded_by=self.user,
            image_path='scans/1/scan1.png',
            original_filename='cxr_01.png',
            file_type='image/png',
            file_size=10240,
        )
        self.diag1 = Diagnosis.objects.create(
            scan=self.scan1,
            detection_result='Positive',
            model_confidence=0.985,
            gradcam_image_path='scans/1/scan1_heatmap.png',
            radiologist_notes='Consolidation observed in right lower lobe.',
            created_by=self.user,
        )

    @patch('patients.views.get_signed_url')
    def test_history_by_numeric_id(self, mock_get_signed_url):
        mock_get_signed_url.return_value = 'https://fake-supabase/signed.png'
        
        response = self.client.get(f'/api/patients/{self.patient.id}/history/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['patient_id'], 'PT-HIST-001')
        self.assertEqual(response.data['total_scans'], 1)
        self.assertEqual(len(response.data['scans']), 1)
        self.assertEqual(response.data['scans'][0]['status'], 'Positive')
        self.assertEqual(response.data['scans'][0]['original_image_url'], 'https://fake-supabase/signed.png')
        self.assertEqual(response.data['scans'][0]['heatmap_image_url'], 'https://fake-supabase/signed.png')
        self.assertEqual(response.headers.get('Cache-Control'), 'no-store, no-cache, must-revalidate, private')

        # Verify audit log
        self.assertTrue(
            AuditLog.objects.filter(action='patient_history_viewed', target_object=f'Patient:{self.patient.id}').exists()
        )

    @patch('patients.views.get_signed_url')
    def test_history_by_alphanumeric_patient_id(self, mock_get_signed_url):
        mock_get_signed_url.return_value = 'https://fake-supabase/signed.png'

        response = self.client.get(f'/api/patients/{self.patient.patient_id}/history/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['patient_id'], 'PT-HIST-001')
        self.assertEqual(response.data['total_scans'], 1)

    def test_history_not_found(self):
        response_str = self.client.get('/api/patients/NONEXISTENT-ID/history/')
        self.assertEqual(response_str.status_code, 404)

        response_num = self.client.get('/api/patients/999999/history/')
        self.assertEqual(response_num.status_code, 404)

    def test_history_unauthenticated(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(f'/api/patients/{self.patient.id}/history/')
        self.assertEqual(response.status_code, 403)
