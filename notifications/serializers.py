"""Serializers for notifications."""
from rest_framework import serializers
from .models import Notification, NotificationPreference


class NotificationSerializer(serializers.ModelSerializer):
    """Serialize notifications."""
    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'title', 'message',
            'data', 'is_read', 'created_at', 'read_at'
        ]
        read_only_fields = ['id', 'created_at', 'read_at']


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serialize notification preferences."""
    class Meta:
        model = NotificationPreference
        fields = [
            'new_report', 'status_update', 'assignment', 'emergency', 'comment',
            'email_enabled', 'sms_enabled', 'push_enabled',
            'digest_mode', 'digest_frequency',
            'dnd_enabled', 'dnd_start', 'dnd_end',
            'category_preferences',
        ]
