from rest_framework import serializers
from django.contrib.auth import get_user_model
from storage.service import get_signed_url

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'title', 'department', 'license_number', 'bio', 'first_name', 'last_name', 'avatar_url']
        read_only_fields = ['id', 'role']

    def get_avatar_url(self, obj):
        if obj.avatar_url:
            return obj.avatar_url
        if obj.avatar_path:
            try:
                return get_signed_url("respiscan-scans", obj.avatar_path, expires_in=2592000)
            except Exception:
                return None
        return None


class EmployeeSerializer(serializers.ModelSerializer):
    """Full serializer for admin CRUD on employee accounts."""
    password = serializers.CharField(write_only=True, required=False)
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'title', 'department', 'license_number', 'bio',
            'is_active', 'date_joined', 'password', 'avatar_url',
        ]
        read_only_fields = ['id', 'date_joined']

    def get_avatar_url(self, obj):
        if obj.avatar_url:
            return obj.avatar_url
        if obj.avatar_path:
            try:
                return get_signed_url("respiscan-scans", obj.avatar_path, expires_in=2592000)
            except Exception:
                return None
        return None

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_password('RespiScan2026!')  # default temp password
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance

class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'first_name', 'last_name']

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
            role='employee',  # Always default — admin accounts via Django admin or admin-only endpoints only
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        user.is_active = False
        user.save()
        return user

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(
        choices=['admin', 'employee'],
        required=False,
        allow_null=True,
        help_text="Optional: if provided, the backend will reject login if the user's role does not match."
    )
