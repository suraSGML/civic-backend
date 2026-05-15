"""
Notification models for in-app, email, and SMS alerts.
"""
from django.db import models
from django.conf import settings


class NotificationType(models.TextChoices):
    REPORT_SUBMITTED = 'report_submitted', 'Report Submitted'
    REPORT_STATUS_UPDATE = 'report_status_update', 'Report Status Update'
    REPORT_ASSIGNED = 'report_assigned', 'Report Assigned'
    REPORT_RESOLVED = 'report_resolved', 'Report Resolved'
    EMERGENCY_ALERT = 'emergency_alert', 'Emergency Alert'
    ASSIGNMENT_RECEIVED = 'assignment_received', 'Assignment Received'
    COMMENT_ADDED = 'comment_added', 'Comment Added'
    SYSTEM = 'system', 'System Notification'


class Notification(models.Model):
    """In-app notification for users."""
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    notification_type = models.CharField(
        max_length=50,
        choices=NotificationType.choices,
        db_index=True,
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    data = models.JSONField(default=dict, blank=True)  # Extra context (report_id, etc.)
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
        ]

    def __str__(self):
        return f'{self.notification_type} → {self.recipient}'

    def mark_read(self):
        from django.utils import timezone
        self.is_read = True
        self.read_at = timezone.now()
        self.save()


class NotificationPreference(models.Model):
    """User notification preferences."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_preferences',
    )
    
    # Notification types
    new_report = models.BooleanField(default=True)
    status_update = models.BooleanField(default=True)
    assignment = models.BooleanField(default=True)
    emergency = models.BooleanField(default=True)
    comment = models.BooleanField(default=True)
    
    # Channels
    email_enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=False)
    push_enabled = models.BooleanField(default=True)
    
    # Digest mode
    digest_mode = models.BooleanField(default=False)
    digest_frequency = models.CharField(
        max_length=20,
        choices=[('daily', 'Daily'), ('weekly', 'Weekly')],
        default='daily',
    )
    
    # Do not disturb
    dnd_enabled = models.BooleanField(default=False)
    dnd_start = models.TimeField(default='22:00')
    dnd_end = models.TimeField(default='08:00')
    
    # Category-specific preferences (stored as JSON)
    category_preferences = models.JSONField(
        default=dict,
        blank=True,
        help_text='Category-specific notification settings'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'notification_preferences'
    
    def __str__(self):
        return f'Preferences for {self.user}'
