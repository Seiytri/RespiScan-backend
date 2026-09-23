import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from patients.models import Patient
from diagnostics.models import Scan, Diagnosis
from django.contrib.auth import get_user_model

User = get_user_model()

# Filipino first names
MALE_FIRST = ['Juan', 'Carlos', 'Miguel', 'Jose', 'Pedro', 'Rafael', 'Marco', 'Antonio', 'Diego', 'Gabriel',
              'Andres', 'Emilio', 'Roberto', 'Enrique', 'Santiago', 'Luis', 'Fernando', 'Manuel', 'Joaquin', 'Daniel']
FEMALE_FIRST = ['Maria', 'Ana', 'Rosa', 'Luz', 'Carmen', 'Isabella', 'Sofia', 'Gabriela', 'Patricia', 'Elena',
                'Cristina', 'Andrea', 'Beatriz', 'Diana', 'Jasmine', 'Nicole', 'Angela', 'Teresa', 'Camille', 'Bianca']
LAST_NAMES = ['Santos', 'Reyes', 'Cruz', 'Garcia', 'Dela Cruz', 'Lopez', 'Torres', 'Ramos', 'Mendoza', 'Rivera',
              'Flores', 'Gonzales', 'Bautista', 'Aquino', 'Villanueva', 'Hernandez', 'Castro', 'Navarro', 'Tan', 'Lim']


class Command(BaseCommand):
    help = 'Seed demo patients, scans, and diagnoses for analytics testing'

    def add_arguments(self, parser):
        parser.add_argument('--patients', type=int, default=60, help='Number of patients to create')

    def handle(self, *args, **options):
        count = options['patients']
        now = timezone.now()

        # Get or create a user to attribute scans to
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            admin_user = User.objects.first()

        created_patients = 0
        created_scans = 0
        created_diagnoses = 0

        for i in range(count):
            gender = random.choice(['Male', 'Female'])
            if gender == 'Male':
                first = random.choice(MALE_FIRST)
            else:
                first = random.choice(FEMALE_FIRST)
            last = random.choice(LAST_NAMES)
            name = f"{first} {last}"

            # Weighted age distribution — more children and elderly for pneumonia realism
            age_group = random.choices(
                ['infant', 'child', 'teen', 'young_adult', 'adult', 'middle', 'senior'],
                weights=[10, 15, 8, 12, 15, 18, 22],
                k=1
            )[0]
            age_ranges = {
                'infant': (0, 5), 'child': (6, 12), 'teen': (13, 17),
                'young_adult': (18, 30), 'adult': (31, 45),
                'middle': (46, 60), 'senior': (61, 90),
            }
            lo, hi = age_ranges[age_group]
            age = random.randint(lo, hi)

            patient_id = f"RSP-{2026}{i + 1:04d}"

            # Skip if patient_id already exists
            if Patient.objects.filter(patient_id=patient_id).exists():
                continue

            created_date = now - timedelta(days=random.randint(1, 180))

            patient = Patient.objects.create(
                patient_id=patient_id,
                name=name,
                age=age,
                gender=gender,
                contact_number=f"+63 9{random.randint(10, 99):02d} {random.randint(100, 999):03d} {random.randint(1000, 9999):04d}",
                status='Pending',
                is_active=True,
                created_at=created_date,
            )
            created_patients += 1

            # Each patient gets 1-3 scans
            num_scans = random.choices([1, 2, 3], weights=[60, 30, 10], k=1)[0]
            for j in range(num_scans):
                scan_date = created_date + timedelta(days=random.randint(0, 14), hours=random.randint(0, 23))
                if scan_date > now:
                    scan_date = now - timedelta(hours=random.randint(1, 48))

                scan = Scan.objects.create(
                    patient=patient,
                    uploaded_by=admin_user,
                    image_path=f"scans/{patient_id}_scan_{j + 1}.dcm",
                    original_filename=f"{patient_id}_cxr_{j + 1}.dcm",
                    file_type="image/dicom",
                    file_size=random.randint(800000, 4000000),
                )
                # Override auto_now_add
                Scan.objects.filter(pk=scan.pk).update(upload_timestamp=scan_date)

                created_scans += 1

                # Positive rate weighted by age (seniors/infants more likely positive)
                if age_group in ('infant', 'senior'):
                    positive_weight = 55
                elif age_group in ('child', 'middle'):
                    positive_weight = 35
                else:
                    positive_weight = 20

                is_positive = random.randint(1, 100) <= positive_weight
                result = 'Positive' if is_positive else 'Negative'
                confidence = round(random.uniform(0.72, 0.98) if is_positive else random.uniform(0.05, 0.35), 4)

                diagnosis = Diagnosis.objects.create(
                    scan=scan,
                    model_confidence=confidence,
                    detection_result=result,
                    gradcam_image_path=f"gradcam/{patient_id}_cam_{j + 1}.png" if is_positive else "",
                    radiologist_notes="" if random.random() > 0.3 else "Reviewed. Findings consistent with AI prediction.",
                    created_by=admin_user,
                )
                created_diagnoses += 1

            # Update patient status based on latest diagnosis
            latest = Diagnosis.objects.filter(scan__patient=patient).order_by('-created_at').first()
            if latest:
                patient.status = latest.detection_result
                patient.last_scan_date = now - timedelta(days=random.randint(0, 30))
                patient.save()

        self.stdout.write(self.style.SUCCESS(
            f"Created {created_patients} patients, {created_scans} scans, {created_diagnoses} diagnoses."
        ))
