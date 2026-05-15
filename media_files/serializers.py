"""Serializers for media files."""
from rest_framework import serializers
from .models import MediaFile


class MediaFileSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = MediaFile
        fields = [
            'id', 'file_url', 'media_type', 'original_filename',
            'file_size', 'latitude', 'longitude', 'captured_at',
            'is_verified', 'is_resolution_proof', 'created_at',
        ]

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file_url


class MediaFileUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = MediaFile
        fields = [
            'file', 'media_type', 'latitude', 'longitude',
            'captured_at', 'is_resolution_proof',
        ]

    def validate_file(self, value):
        from django.conf import settings
        # Validate file type
        allowed_types = [
            'image/jpeg', 'image/png', 'image/gif', 'image/webp',
            'video/mp4', 'video/avi', 'video/quicktime',
            'audio/mpeg', 'audio/wav', 'audio/ogg',
        ]
        if hasattr(value, 'content_type') and value.content_type not in allowed_types:
            raise serializers.ValidationError(
                f'Unsupported file type: {value.content_type}'
            )
        return value
