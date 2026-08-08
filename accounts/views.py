from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from django.http import JsonResponse
from rest_framework import status, views
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django_otp.plugins.otp_totp.models import TOTPDevice

from .serializers import UserSerializer, LoginSerializer, SignupSerializer
from .totp_serializers import TOTPVerifySerializer
from audit.service import log_action


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
            user = authenticate(
                request,
                username=serializer.validated_data['username'],
                password=serializer.validated_data['password'],
            )
            if user is None:
                return Response(
                    {'error': 'Invalid credentials'},
                    status=status.HTTP_401_UNAUTHORIZED,
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
