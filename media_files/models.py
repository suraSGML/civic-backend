"""
Media file models for report evidence (images, videos, audio).
"""
import os
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError


class MediaType(models.TextChoices):
    IMAGE = 'image', 'Image'
    VIDEO = 'video', 'Video'
    AUDIO = 'audio', 'Audio'
    DOCUMENT = 'document', 'Document'


def report_media_upload_path(instance, filename):
    """Organize uploads by report ID."""
    ext = filename.rsplit('.', 1)[-1].lower()
    return f'reports/{instance.report_id}/{instance.media_type}/{filename}'


def validate_file_size(value):
    max_size = settings.MAX_VIDEO_SIZE
    if value.size > max_size:
        raise ValidationError(f'File size cannot exceed {max_size // (1024*1024)}MB.')


class MediaFile(models.Model):
    """
    Evidence files attached to a report.
    Supports images, videos, and audio notes.
    """
    report = models.ForeignKey(
        'reports.Report',
        on_delete=models.CASCADE,
        related_name='media_files',
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
    )
    file = models.FileField(
        upload_to=report_media_upload_path,
        validators=[validate_file_size],
    )
    media_type = models.CharField(max_length=20, choices=MediaType.choices)
    original_filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(default=0)  # bytes
    mime_type = models.CharField(max_length=100, blank=True)

    # Location metadata from device
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    captured_at = models.DateTimeField(null=True, blank=True)

    # Moderation
    is_verified = models.BooleanField(default=False)
    is_flagged = models.BooleanField(default=False)
    flag_reason = models.TextField(blank=True)

    # Resolution proof (uploaded by workers)
    is_resolution_proof = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'media_files'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.media_type} for Report #{self.report_id}'

    @property
    def file_url(self):
        if self.file:
            return self.file.url
        return None

    def save(self, *args, **kwargs):
        if self.file:
            self.original_filename = os.path.basename(self.file.name)
            self.file_size = self.file.size
            # Auto-detect media type from mime
            if not self.media_type:
                name = self.file.name.lower()
                if any(name.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                    self.media_type = MediaType.IMAGE
                elif any(name.endswith(ext) for ext in ['.mp4', '.avi', '.mov', '.mkv']):
                    self.media_type = MediaType.VIDEO
                elif any(name.endswith(ext) for ext in ['.mp3', '.wav', '.ogg', '.m4a']):
                    self.media_type = MediaType.AUDIO
                else:
                    self.media_type = MediaType.DOCUMENT
        super().save(*args, **kwargs)
