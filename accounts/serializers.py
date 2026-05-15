"""
Serializers for user accounts.
"""
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, UserRole


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            'email', 'first_name', 'last_name', 'phone',
            'password', 'password_confirm', 'city', 'region',
        ]
        extra_kwargs = {
            'phone': {'required': False, 'allow_blank': True},
            'city': {'required': False, 'allow_blank': True},
            'region': {'required': False, 'allow_blank': True},
        }

    def validate(self, attrs):
        if attrs['password'] != attrs.pop('password_confirm'):
            raise serializers.ValidationError({'password': 'Passwords do not match.'})
        return attrs

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user


class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        user = authenticate(username=email, password=password)

        if not user:
            raise serializers.ValidationError('Invalid email or password.')
        if not user.is_active:
            raise serializers.ValidationError('Account is deactivated.')
        if user.is_banned:
            raise serializers.ValidationError(f'Account is banned. Reason: {user.ban_reason}')

        refresh = RefreshToken.for_user(user)
        return {
            'user': user,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }


class UserProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    total_reports = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'phone', 'role', 'avatar', 'bio', 'city', 'region',
            'latitude', 'longitude', 'is_verified', 'department',
            'employee_id', 'specialization', 'date_joined',
            'notify_email', 'notify_sms', 'notify_push', 'total_reports',
        ]
        read_only_fields = ['id', 'email', 'role', 'is_verified', 'date_joined']

    def get_full_name(self, obj):
        return obj.get_full_name()

    def get_total_reports(self, obj):
        if hasattr(obj, 'reports'):
            return obj.reports.count()
        return 0


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'phone', 'bio',
            'city', 'region', 'latitude', 'longitude',
            'notify_email', 'notify_sms', 'notify_push',
            'department', 'specialization',
        ]


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({'new_password': 'Passwords do not match.'})
        return attrs

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Old password is incorrect.')
        return value


class AdminUserSerializer(serializers.ModelSerializer):
    """Serializer for admin user management."""
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'phone',
            'role', 'is_active', 'is_verified', 'is_banned',
            'ban_reason', 'city', 'region', 'department',
            'employee_id', 'date_joined', 'last_login',
        ]
        read_only_fields = ['id', 'date_joined', 'last_login']


class WorkerListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for worker assignment dropdowns."""
    full_name = serializers.SerializerMethodField()
    active_assignments = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'full_name', 'email', 'phone', 'department',
                  'specialization', 'active_assignments']

    def get_full_name(self, obj):
        return obj.get_full_name()

    def get_active_assignments(self, obj):
        return obj.assignments.filter(status__in=['pending', 'in_progress']).count()
