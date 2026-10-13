from django.contrib.auth import authenticate, login, logout, get_user_model
from django.middleware.csrf import get_token
from django.http import JsonResponse
from rest_framework import status, views, viewsets, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser, BasePermission
from django_otp.plugins.otp_totp.models import TOTPDevice

from .serializers import UserSerializer, LoginSerializer, SignupSerializer, EmployeeSerializer
from .totp_serializers import TOTPVerifySerializer
from audit.service import log_action
from storage.service import upload_file, delete_file, get_signed_url
import uuid

User = get_user_model()

def _get_client_ip(request):
    """Extract the client IP from the request, respecting X-Forwarded-For."""
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


class CSRFTokenView(views.APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return JsonResponse({'csrfToken': get_token(request)})


class SignupView(views.APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            log_action(
                user=user,
                action="user_signup",
                target_object=f"User:{user.pk}",
                metadata={"ip": _get_client_ip(request), "username": user.username},
            )
            return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(views.APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            username_or_email = serializer.validated_data['username']
            password = serializer.validated_data['password']

            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            # Resolve email to username
            if '@' in username_or_email:
                user_obj = User.objects.filter(email=username_or_email).first()
                if user_obj:
                    username_or_email = user_obj.username

            user = authenticate(
                request,
                username=username_or_email,
                password=password,
            )
            if user is None:
                return Response(
                    {'error': 'Invalid credentials'},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            # --- Role check ---
            # If the frontend specifies a role (via the Employee/Administrator tab),
            # verify the authenticated user actually has that role.
            requested_role = serializer.validated_data.get('role')
            if requested_role:
                user_role = 'admin' if user.is_admin else 'employee'
                if user_role != requested_role:
                    role_label = 'Administrator' if requested_role == 'admin' else 'Employee'
                    return Response(
                        {'error': f'This account is not registered as an {role_label}.'},
                        status=status.HTTP_403_FORBIDDEN,
                    )

            # --- 2FA check ---
            confirmed_devices = TOTPDevice.objects.filter(user=user, confirmed=True)
            if confirmed_devices.exists():
                otp_token = request.data.get("otp_token")
                if not otp_token:
                    # Password OK, but OTP still needed — don't log in yet
                    return Response(
                        {"otp_required": True, "user_id": user.pk},
                        status=status.HTTP_200_OK,
                    )
                # Verify the OTP token against any confirmed device
                device_verified = False
                for device in confirmed_devices:
                    if device.verify_token(otp_token):
                        device_verified = True
                        break
                if not device_verified:
                    return Response(
                        {"error": "Invalid OTP token."},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )

            # All checks passed — complete login
            login(request, user)
            
            # Handle remember me session expiry
            remember_me = request.data.get('remember_me', False)
            if remember_me:
                request.session.set_expiry(1209600)  # 2 weeks
            else:
                request.session.set_expiry(0)  # expires when browser is closed

            log_action(
                user=user,
                action="user_login",
                target_object=f"User:{user.pk}",
                metadata={"ip": _get_client_ip(request)},
            )
            return Response(UserSerializer(user).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class LogoutView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        log_action(
            user=request.user,
            action="user_logout",
            target_object=f"User:{request.user.pk}",
            metadata={"ip": _get_client_ip(request)},
        )
        logout(request)
        return Response({'message': 'Successfully logged out.'})


class UserMeView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AvatarUploadView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        file_obj = request.FILES.get('avatar')
        if not file_obj:
            return Response({"error": "No avatar file provided."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate file type
        allowed_types = ['image/jpeg', 'image/png', 'image/webp']
        if file_obj.content_type not in allowed_types:
            return Response(
                {"error": f"Invalid file type {file_obj.content_type}. Allowed: JPEG, PNG, WEBP."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate file size (max 5MB)
        if file_obj.size > 5 * 1024 * 1024:
            return Response(
                {"error": "Avatar image file size must not exceed 5MB."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = request.user

        # Delete existing avatar if exists
        if user.avatar_path:
            try:
                delete_file(bucket="respiscan-scans", path=user.avatar_path)
            except Exception:
                pass

        ext = file_obj.name.split('.')[-1].lower() if '.' in file_obj.name else 'png'
        storage_path = f"avatars/{user.id}/{uuid.uuid4().hex[:12]}.{ext}"

        try:
            upload_file(
                bucket="respiscan-scans",
                path=storage_path,
                file_data=file_obj.read(),
                content_type=file_obj.content_type
            )
        except Exception as e:
            return Response({"error": f"Failed to upload to storage: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        user.avatar_path = storage_path
        user.avatar_url = get_signed_url(bucket="respiscan-scans", path=storage_path, expires_in=2592000) or None
        user.save(update_fields=['avatar_path', 'avatar_url'])

        log_action(
            user=user,
            action="avatar_uploaded",
            target_object=f"User:{user.pk}",
            metadata={"storage_path": storage_path}
        )

        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)

    def delete(self, request):
        user = request.user
        if user.avatar_path:
            try:
                delete_file(bucket="respiscan-scans", path=user.avatar_path)
            except Exception:
                pass
            user.avatar_path = None
            user.avatar_url = None
            user.save(update_fields=['avatar_path', 'avatar_url'])

            log_action(
                user=user,
                action="avatar_deleted",
                target_object=f"User:{user.pk}",
                metadata={}
            )

        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)


from django.contrib.auth import update_session_auth_hash

class ChangePasswordView(views.APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        user = request.user
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')
        
        if not user.check_password(current_password):
            return Response({"error": "Incorrect current password."}, status=status.HTTP_400_BAD_REQUEST)
            
        user.set_password(new_password)
        user.save()
        
        # Keep the user logged in by updating their session hash
        update_session_auth_hash(request, user)
        
        return Response({"message": "Password updated successfully."})


# ---------------------------------------------------------------------------
# TOTP setup & confirmation
# ---------------------------------------------------------------------------

class TOTPSetupView(views.APIView):
    """
    Create (or retrieve) an unconfirmed TOTP device for the authenticated user
    and return its provisioning URI so the frontend can render a QR code.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        # Re-use an existing unconfirmed device if one exists
        device = TOTPDevice.objects.filter(user=user, confirmed=False).first()
        if device is None:
            device = TOTPDevice.objects.create(
                user=user,
                name="default",
                confirmed=False,
            )

        provisioning_uri = device.config_url
        return Response(
            {"provisioning_uri": provisioning_uri, "device_id": device.pk},
            status=status.HTTP_200_OK,
        )


class TOTPConfirmView(views.APIView):
    """
    Verify a TOTP token against the user's unconfirmed device.
    If valid, mark the device as confirmed — 2FA is now active.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = TOTPVerifySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        device = TOTPDevice.objects.filter(user=user, confirmed=False).first()
        if device is None:
            return Response(
                {"error": "No pending TOTP device found. Call /api/auth/totp/setup/ first."},
                status=status.HTTP_404_NOT_FOUND,
            )

        token = serializer.validated_data["token"]
        if not device.verify_token(token):
            return Response(
                {"error": "Invalid token. Please try again."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        device.confirmed = True
        device.save()

        log_action(
            user=user,
            action="totp_device_confirmed",
            target_object=f"TOTPDevice:{device.pk}",
            metadata={"device_name": device.name},
        )

        return Response(
            {"message": "TOTP device confirmed. Two-factor authentication is now active."},
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# Employee management (Admin only)
# ---------------------------------------------------------------------------

class IsAdminOrStaff(BasePermission):
    """Allows access to users who have admin role or is_staff flag."""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            (request.user.is_staff or getattr(request.user, 'role', '') == 'admin' or request.user.is_superuser)
        )


class EmployeeViewSet(viewsets.ModelViewSet):
    """
    Admin-only viewset for managing employee and co-administrator accounts.
    Supports full CRUD + approve/deactivate/reset-password actions.
    """
    serializer_class = EmployeeSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsAdminOrStaff()]

    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['username', 'first_name', 'last_name', 'email', 'department']
    ordering_fields = ['date_joined', 'first_name', 'last_name']
    ordering = ['-date_joined']

    def get_queryset(self):
        return User.objects.all().order_by('-date_joined')

    def perform_destroy(self, instance):
        """Soft-delete: deactivate instead of hard-deleting."""
        instance.is_active = False
        instance.save()
        log_action(
            user=self.request.user,
            action="employee_deactivated",
            target_object=f"User:{instance.pk}",
            metadata={"username": instance.username},
        )

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Activate a pending employee account."""
        user = self.get_object()
        user.is_active = True
        user.save()
        log_action(
            user=request.user,
            action="employee_approved",
            target_object=f"User:{user.pk}",
            metadata={"username": user.username},
        )
        return Response(EmployeeSerializer(user).data)

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate an employee account."""
        user = self.get_object()
        user.is_active = False
        user.save()
        log_action(
            user=request.user,
            action="employee_deactivated",
            target_object=f"User:{user.pk}",
            metadata={"username": user.username},
        )
        return Response(EmployeeSerializer(user).data)

    @action(detail=True, methods=['post'], url_path='reset-password')
    def reset_password(self, request, pk=None):
        """
        Securely reset any user account password (employee or co-administrator).
        Logs an audit trail record attributing the reset to the executing administrator.
        """
        user = self.get_object()
        new_password = request.data.get('password')
        if not new_password or len(str(new_password).strip()) < 8:
            return Response(
                {"error": "Password must be at least 8 characters long."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new_password)
        user.save()

        log_action(
            user=request.user,
            action="password_reset_by_admin",
            target_object=f"User:{user.pk}",
            metadata={
                "target_username": user.username,
                "target_role": user.role,
                "admin_username": request.user.username,
            }
        )

        return Response({
            "message": f"Password for {user.username} has been reset successfully."
        }, status=status.HTTP_200_OK)


from .models import DeviceSession
from django.contrib.sessions.models import Session

def parse_user_agent(ua_string):
    if not ua_string:
        return 'Unknown Device'
        
    browser = 'Unknown Browser'
    if 'Edg' in ua_string: browser = 'Edge'
    elif 'Chrome' in ua_string: browser = 'Chrome'
    elif 'Firefox' in ua_string: browser = 'Firefox'
    elif 'Safari' in ua_string: browser = 'Safari'
    
    os = 'Unknown OS'
    if 'Windows' in ua_string: os = 'Windows'
    elif 'Mac OS' in ua_string: os = 'macOS'
    elif 'Linux' in ua_string: os = 'Linux'
    elif 'Android' in ua_string: os = 'Android'
    elif 'iPhone' in ua_string or 'iPad' in ua_string: os = 'iOS'
    
    return f'{browser} · {os}'

class ActiveSessionsView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        sessions = DeviceSession.objects.filter(user=request.user).order_by('-last_activity')
        current_session_key = request.session.session_key
        
        data = []
        for s in sessions:
            # Cleanup expired sessions lazily
            if not Session.objects.filter(session_key=s.session_key).exists():
                s.delete()
                continue
                
            is_current = (s.session_key == current_session_key)
            from django.utils.timesince import timesince
            
            data.append({
                'id': s.session_key,
                'device': parse_user_agent(s.user_agent),
                'location': s.ip_address,
                'current': is_current,
                'when': 'Now' if is_current else f'{timesince(s.last_activity)} ago',
            })
            
        return Response(data)
        
    def delete(self, request, session_key):
        # Revoke a specific session
        if session_key == request.session.session_key:
            return Response({'error': 'Cannot revoke current session. Use logout instead.'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            device_session = DeviceSession.objects.get(user=request.user, session_key=session_key)
            device_session.delete()
            Session.objects.filter(session_key=session_key).delete()
            return Response({'message': 'Session revoked successfully.'})
        except DeviceSession.DoesNotExist:
            return Response({'error': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)
