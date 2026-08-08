from rest_framework import serializers


class TOTPVerifySerializer(serializers.Serializer):
    """Validates a 6-digit TOTP token."""
    token = serializers.CharField(
        max_length=6,
        min_length=6,
        help_text="6-digit TOTP code from the authenticator app.",
    )
