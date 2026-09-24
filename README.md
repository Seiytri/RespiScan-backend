# RespiScan Backend

A Django REST Framework API for AI-powered bacterial pneumonia detection from chest X-ray images. This is the backend companion to the [RespiScan Frontend](https://github.com/RalfNeis/RespisScan-Frontend).

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [Project Structure](#project-structure)
- [Django Applications](#django-applications)
- [API Reference](#api-reference)
- [Authentication](#authentication)
- [Inference Pipeline](#inference-pipeline)
- [Asynchronous Processing](#asynchronous-processing)
- [Database Models](#database-models)
- [Management Commands](#management-commands)
- [Development Notes](#development-notes)

---

## Overview

RespiScan is a clinical diagnostic platform that accepts chest X-ray uploads, processes them through a DenseNet-121 deep learning model, and returns pneumonia detection results with Grad-CAM heatmap visualizations. The backend handles user authentication, patient record management, scan processing, report generation, notification preferences, and audit logging.

## Architecture

The system is composed of the following services:

- **Django API Server** -- serves the REST API on port 8000 using session-based authentication.
- **Celery Worker** -- processes scan inference tasks asynchronously so upload requests return immediately.
- **Redis** -- message broker for Celery task dispatch.
- **Supabase Storage** -- remote object storage for CXR images and Grad-CAM heatmap files.
- **External Inference API** -- a separate model-serving endpoint (ngrok-hosted) that accepts CXR images and returns predictions with Grad-CAM overlays.
- **SQLite** -- default development database (PostgreSQL supported for production via `DATABASE_URL`).

```
Frontend (:3000)
    |
    | /api/* (proxied)
    v
Django REST API (:8000)
    |
    |--- Celery Worker ---> External Inference API (DenseNet-121)
    |         |
    |         v
    |    Supabase Storage (CXR images, heatmaps)
    |
    |--- SQLite / PostgreSQL
    |
    v
  Redis (:6379)
```

## Technology Stack

| Component          | Technology                                     |
| :----------------- | :--------------------------------------------- |
| Framework          | Django 5.2, Django REST Framework 3.17         |
| Authentication     | Session cookies, CSRF tokens, django-otp (TOTP)|
| Task Queue         | Celery 5.6 with Redis broker                   |
| Object Storage     | Supabase Storage (via `supabase-py`)           |
| Database           | SQLite (dev), PostgreSQL (prod via psycopg2)   |
| Image Inference    | External HTTP API (DenseNet-121 + Grad-CAM)    |
| Email              | Resend (production), console backend (dev)     |
| Environment Config | django-environ                                 |

## Prerequisites

- **Python** 3.10 or later
- **Redis** (required for Celery; install via your package manager or Docker)
- **Supabase** project with a storage bucket named `respiscan-scans` (for scan uploads)
- A running inference API endpoint (configured via `INFERENCE_API_URL`)

## Getting Started

1. **Clone the repository**

   ```bash
   git clone https://github.com/RalfNeis/RespiScan-backend.git
   cd RespiScan-backend
   ```

2. **Create and activate a virtual environment**

   ```bash
   python -m venv venv

   # Windows
   venv\Scripts\activate

   # macOS / Linux
   source venv/bin/activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**

   Copy the example file and update the values:

   ```bash
   cp .env.example .env
   ```

   See the [Environment Variables](#environment-variables) section below for details.

5. **Apply database migrations**

   ```bash
   python manage.py migrate
   ```

6. **Create an admin account**

   ```bash
   python manage.py createsuperuser
   ```

7. **Start the development server**

   ```bash
   python manage.py runserver
   ```

   The API will be available at [http://localhost:8000](http://localhost:8000).

8. **(Optional) Start the Celery worker for scan processing**

   In a separate terminal, with the virtual environment activated:

   ```bash
   celery -A respiscan worker --loglevel=info
   ```

9. **(Optional) Seed demo data**

   ```bash
   python manage.py seed_demo_data
   ```

   This populates the database with 50 sample patients and randomized scan results. It does not create user accounts.

## Environment Variables

Configure these in the `.env` file at the project root:

| Variable                   | Description                                                       | Default / Example                                     |
| :------------------------- | :---------------------------------------------------------------- | :---------------------------------------------------- |
| `DEBUG`                    | Enable Django debug mode                                          | `True`                                                |
| `SECRET_KEY`               | Django secret key (replace in production)                         | `django-insecure-example-secret-key-replace-in-prod`  |
| `ALLOWED_HOSTS`            | Comma-separated list of allowed hostnames                         | `localhost,127.0.0.1`                                 |
| `DATABASE_URL`             | Database connection string (optional; defaults to SQLite)         | `sqlite:///db.sqlite3`                                |
| `SUPABASE_URL`             | Supabase project URL                                              | `https://your-project.supabase.co`                    |
| `SUPABASE_SERVICE_ROLE_KEY`| Supabase service role key (server-side only, never expose)        | `your-supabase-service-role-key`                      |
| `INFERENCE_API_URL`        | URL of the model-serving inference endpoint                       | `https://your-endpoint.ngrok-free.dev`                |
| `EMAIL_BACKEND`            | Django email backend class                                        | `django.core.mail.backends.console.EmailBackend`      |
| `RESEND_API_KEY`           | Resend API key for production email delivery                      | `your-resend-api-key`                                 |
| `SESSION_COOKIE_SECURE`    | Set to `True` in production (HTTPS only)                          | `False`                                               |
| `FRONTEND_URL`             | Frontend origin for CORS and email links                          | `http://localhost:3000`                                |
| `REDIS_URL`                | Redis connection URL for Celery broker                            | `redis://localhost:6379/0`                             |

> **Note on DATABASE_URL:** If you omit this variable, Django defaults to an SQLite database at `<project_root>/db.sqlite3` using an absolute path. If you provide a custom value, use an absolute path (e.g. `sqlite:////home/user/project/db.sqlite3` with four slashes) to avoid working-directory issues.

## Project Structure

```
RespiScan-backend/
├── manage.py                        # Django management entry point
├── requirements.txt                 # Python dependencies
├── .env                             # Environment configuration (gitignored)
├── .env.example                     # Environment template
├── db.sqlite3                       # SQLite database (gitignored)
├── respiscan/                       # Django project configuration
│   ├── settings.py                  # Settings (database, auth, middleware, etc.)
│   ├── urls.py                      # Root URL router
│   ├── celery.py                    # Celery application setup
│   └── wsgi.py / asgi.py           # WSGI/ASGI entry points
├── accounts/                        # User authentication and management
│   ├── models.py                    # User, DeviceSession
│   ├── views.py                     # Login, signup, profile, TOTP, sessions
│   ├── serializers.py               # User, Login, Signup, Employee serializers
│   ├── totp_serializers.py          # TOTP verification serializer
│   └── urls.py                      # Auth and employee API routes
├── patients/                        # Patient record management
│   ├── models.py                    # Patient
│   ├── views.py                     # PatientViewSet (CRUD)
│   ├── serializers.py               # Patient serializer
│   └── urls.py                      # Patient API routes
├── diagnostics/                     # CXR scan upload, inference, and export
│   ├── models.py                    # Scan, Diagnosis
│   ├── views.py                     # ScanUploadView, ScanResultView, ExportPDFView
│   ├── tasks.py                     # Celery task for async inference
│   ├── serializers.py               # Scan and Diagnosis serializers
│   └── urls.py                      # Diagnostics API routes
├── inference/                       # AI model integration
│   └── service.py                   # run_inference() -- calls external API
├── storage/                         # File storage abstraction
│   └── service.py                   # upload_file(), get_signed_url(), delete_file()
├── reports/                         # Analytics report generation
│   ├── models.py                    # Report
│   ├── views.py                     # ReportListView, ReportGenerateView
│   └── urls.py                      # Report API routes
├── notifications/                   # Notification preferences
│   ├── models.py                    # NotificationPreference
│   ├── views.py                     # NotificationPreferencesView
│   └── urls.py                      # Notification API routes
├── audit/                           # Security audit trail
│   ├── models.py                    # AuditLog
│   └── service.py                   # log_action() helper
└── core/                            # Shared utilities and analytics
    ├── models.py                    # SystemSettings (singleton)
    ├── views.py                     # AnalyticsView, SystemSettingsView
    └── management/
        └── commands/
            └── seed_demo_data.py    # Demo data seeder
```

## Django Applications

### accounts

Handles user registration, authentication, profile management, password changes, two-factor authentication (TOTP), active session tracking, and admin-level employee management. Users have a `role` field (employee or admin) that controls access across the system.

### patients

Provides full CRUD operations for patient records including demographics, contact details, emergency contacts, medical history, and allergies. Supports search and filtering through DRF's filter backends.

### diagnostics

Manages the scan lifecycle: accepts CXR image uploads (stored in Supabase), dispatches inference tasks to Celery, stores detection results and Grad-CAM heatmaps, and exports clinical PDF reports for individual scans.

### inference

A service layer that communicates with the external DenseNet-121 model API. Sends image bytes via multipart POST and parses the response into a prediction label, confidence score, and Grad-CAM heatmap image.

### storage

Abstracts all interactions with Supabase Storage. Provides functions to upload files, generate time-limited signed URLs for frontend access, and delete files. The Supabase service role key never leaves the server.

### reports

Generates and stores analytical PDF reports summarizing scan activity over configurable date ranges. Tracks scan totals, positive/negative counts, and narrative summaries.

### notifications

Stores per-user notification preferences (new results, system updates, report generation, security alerts, email delivery toggle).

### audit

Records security-relevant events (logins, logouts, account changes, TOTP setup, employee management actions) in a structured audit log with user, action, target, IP address, and arbitrary metadata. The `log_action()` service function is called from views throughout the project.

### core

Contains shared utilities, the dashboard analytics aggregation view, system-wide AI configuration (confidence threshold, Grad-CAM settings, data retention, audit toggle), and the demo data seeder management command.

## API Reference

All endpoints are prefixed with `/api/`.

### Authentication

| Method | Endpoint                          | Description                          | Auth Required |
| :----- | :-------------------------------- | :----------------------------------- | :------------ |
| GET    | `/api/auth/csrf/`                 | Retrieve a CSRF token                | No            |
| POST   | `/api/auth/signup/`               | Register a new user account          | No            |
| POST   | `/api/auth/login/`                | Authenticate with credentials        | No            |
| POST   | `/api/auth/logout/`               | End the current session              | Yes           |
| GET    | `/api/auth/me/`                   | Retrieve the authenticated user      | Yes           |
| PATCH  | `/api/auth/me/`                   | Update profile fields                | Yes           |
| PATCH  | `/api/auth/me/password/`          | Change password                      | Yes           |
| GET    | `/api/auth/sessions/`             | List active device sessions          | Yes           |
| DELETE | `/api/auth/sessions/<key>/`       | Revoke a specific session            | Yes           |
| POST   | `/api/auth/totp/setup/`           | Initialize TOTP device setup         | Yes           |
| POST   | `/api/auth/totp/confirm/`         | Confirm TOTP with verification code  | Yes           |

### Employee Management (Admin Only)

| Method | Endpoint                                | Description                    |
| :----- | :-------------------------------------- | :----------------------------- |
| GET    | `/api/auth/employees/`                  | List all employees             |
| POST   | `/api/auth/employees/`                  | Create a new employee          |
| GET    | `/api/auth/employees/<id>/`             | Retrieve employee details      |
| PUT    | `/api/auth/employees/<id>/`             | Update an employee             |
| PATCH  | `/api/auth/employees/<id>/`             | Partial update                 |
| DELETE | `/api/auth/employees/<id>/`             | Deactivate an employee         |
| POST   | `/api/auth/employees/<id>/approve/`     | Activate a pending account     |
| POST   | `/api/auth/employees/<id>/deactivate/`  | Deactivate an account          |

### Patients

| Method | Endpoint                  | Description                    |
| :----- | :------------------------ | :----------------------------- |
| GET    | `/api/patients/`          | List all patients              |
| POST   | `/api/patients/`          | Register a new patient         |
| GET    | `/api/patients/<id>/`     | Retrieve patient details       |
| PUT    | `/api/patients/<id>/`     | Update a patient record        |
| PATCH  | `/api/patients/<id>/`     | Partial update                 |
| DELETE | `/api/patients/<id>/`     | Delete a patient record        |

### Diagnostics

| Method | Endpoint                            | Description                            |
| :----- | :---------------------------------- | :------------------------------------- |
| POST   | `/api/diagnostics/upload/`          | Upload a CXR image for inference       |
| GET    | `/api/diagnostics/<scan_id>/`       | Retrieve scan result and status        |
| GET    | `/api/diagnostics/<scan_id>/export/`| Download clinical PDF for a scan       |

### Reports

| Method | Endpoint                    | Description                          |
| :----- | :-------------------------- | :----------------------------------- |
| GET    | `/api/reports/`             | List previously generated reports    |
| POST   | `/api/reports/generate/`    | Generate an analytics PDF report     |

### Analytics and Settings

| Method | Endpoint                             | Description                            |
| :----- | :----------------------------------- | :------------------------------------- |
| GET    | `/api/analytics/dashboard/`          | Dashboard KPIs and aggregated data     |
| GET    | `/api/analytics/system-settings/`    | Retrieve system AI configuration       |
| PATCH  | `/api/analytics/system-settings/`    | Update system AI configuration (admin) |

### Notifications

| Method | Endpoint                             | Description                             |
| :----- | :----------------------------------- | :-------------------------------------- |
| GET    | `/api/notifications/preferences/`    | Retrieve notification preferences       |
| PATCH  | `/api/notifications/preferences/`    | Update notification preferences         |

## Authentication

The API uses Django's session-based authentication with CSRF protection. The typical flow is:

1. **Fetch CSRF token** -- `GET /api/auth/csrf/` returns a token that must be included as the `X-CSRFToken` header in all subsequent mutating requests.
2. **Login** -- `POST /api/auth/login/` with `username` (or `email`), `password`, and optionally `role` and `otp_token`. On success, Django sets a session cookie.
3. **Authenticated requests** -- include the session cookie and CSRF token. All endpoints (except login, signup, and CSRF) require authentication by default.
4. **Logout** -- `POST /api/auth/logout/` clears the session.

### Role-Based Access

Users have one of two roles: `employee` or `admin`. The login endpoint optionally accepts a `role` parameter; if provided, the backend verifies the user's actual role matches before granting access. Admin users (role `admin` or Django superusers) can access employee management and system settings endpoints.

### Two-Factor Authentication

TOTP-based 2FA is supported through `django-otp`. Users set up a TOTP device via `/api/auth/totp/setup/`, scan the provisioning QR code in an authenticator app, and confirm with `/api/auth/totp/confirm/`. Once confirmed, login requires a valid `otp_token` alongside credentials.

## Inference Pipeline

When a chest X-ray is uploaded:

1. The `ScanUploadView` receives the image, uploads it to Supabase Storage, and creates `Scan` and `Diagnosis` database records with a `Pending` status.
2. A Celery task (`process_scan_task`) is dispatched asynchronously.
3. The worker downloads the image from Supabase using a signed URL, sends the raw bytes to the external inference API, and receives back a prediction (`Normal` or `Pneumonia`), a confidence score, and a base64-encoded Grad-CAM heatmap.
4. The heatmap is uploaded to Supabase Storage, and the `Diagnosis` record is updated with the result, confidence, and heatmap path.
5. The frontend polls `GET /api/diagnostics/<scan_id>/` until the status changes from `Pending`.

## Asynchronous Processing

Celery is configured in `respiscan/celery.py` with Redis as the message broker. The broker URL defaults to `redis://localhost:6379/0` and can be overridden via the `REDIS_URL` environment variable.

To run the worker:

```bash
celery -A respiscan worker --loglevel=info
```

On Windows, you may need to use the `eventlet` pool:

```bash
celery -A respiscan worker --loglevel=info --pool=eventlet
```

## Database Models

### User (accounts)

Extends Django's `AbstractUser` with clinical staff fields: `role`, `title`, `department`, `license_number`, and `bio`. The `is_admin` property returns `True` for users with the admin role or Django superuser status.

### DeviceSession (accounts)

Tracks active login sessions per user with `session_key`, `ip_address`, `user_agent`, and `last_activity` for the active sessions management feature.

### Patient (patients)

Stores patient demographics, contact information, emergency contacts, medical history, and allergies. Includes computed `full_name` and `age` properties.

### Scan (diagnostics)

Records each uploaded CXR image with its Supabase storage path, associated patient, uploading user, scan type, and optional notes.

### Diagnosis (diagnostics)

One-to-one with Scan. Stores the AI detection result (`Pending`, `Positive`, or `Negative`), model confidence score (0 to 1), and Grad-CAM heatmap storage path.

### Report (reports)

Represents a generated analytics PDF with its date range, summary statistics (total scans, positive and negative counts), narrative summary, and file storage path.

### NotificationPreference (notifications)

One-to-one with User. Boolean toggles for new results, system updates, report generation, security alerts, and email delivery.

### AuditLog (audit)

Immutable log entries recording user actions with action type, target object identifier, IP address, and a JSON metadata field for additional context.

### SystemSettings (core)

A singleton model storing system-wide AI configuration: confidence threshold, Grad-CAM rendering defaults (enabled, opacity, colormap), data retention period, and audit logging toggle.

## Management Commands

### seed_demo_data

Populates the database with sample data for development and testing:

```bash
python manage.py seed_demo_data
```

This creates 50 patients with randomized Filipino demographics and 2 to 5 scans per patient with synthetic diagnosis results. It does not create user accounts; use `createsuperuser` or the signup endpoint for that.

## Development Notes

- **Database path:** The default database is stored at `<project_root>/db.sqlite3` using an absolute path derived from `BASE_DIR`. If you set `DATABASE_URL` in `.env`, use an absolute path to avoid the database resolving to different locations depending on your working directory.
- **CORS:** `django-cors-headers` is installed and the frontend origin (`FRONTEND_URL`) should be added to the allowed origins in production.
- **Soft deletes:** The `EmployeeViewSet.perform_destroy()` method deactivates accounts rather than permanently deleting them, preserving audit history.
- **Supabase credentials:** The service role key is used server-side only. It must never appear in API responses, logs, or frontend code.
- **Email:** In development, emails are printed to the console via `django.core.mail.backends.console.EmailBackend`. For production, configure the Resend API key.
- **PostgreSQL:** Production deployments can switch to PostgreSQL by setting `DATABASE_URL` to a Postgres connection string (e.g. `postgres://user:pass@host:5432/dbname`). The `psycopg2-binary` driver is already included in the requirements.
