"""
Core models: AuditLog for security tracking.
"""
from django.db import models
from django.conf import settings


class AuditLog(models.Model):
    """
    Full audit trail of all user actions.
    Critical for security, compliance, and fraud detection.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_logs',
    )
    action = models.CharField(max_length=500)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    status_code = models.PositiveSmallIntegerField(null=True, blank=True)
    extra_data = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'audit_logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
        ]

    def __str__(self):
        return f'{self.user} | {self.action} | {self.timestamp}'
