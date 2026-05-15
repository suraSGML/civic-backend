"""
Assignment models for task management.
Authorities assign reports to field workers.
"""
from django.db import models
from django.conf import settings


class AssignmentStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    ACCEPTED = 'accepted', 'Accepted'
    IN_PROGRESS = 'in_progress', 'In Progress'
    COMPLETED = 'completed', 'Completed'
    CANCELLED = 'cancelled', 'Cancelled'
    REASSIGNED = 'reassigned', 'Reassigned'


class Assignment(models.Model):
    """
    Links a report to a field worker for resolution.
    """
    report = models.ForeignKey(
        'reports.Report',
        on_delete=models.CASCADE,
        related_name='assignments',
    )
    worker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='assignments',
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_assignments',
    )
    status = models.CharField(
        max_length=20,
        choices=AssignmentStatus.choices,
        default=AssignmentStatus.PENDING,
        db_index=True,
    )
    priority = models.PositiveSmallIntegerField(default=1)  # 1=normal, 2=high, 3=urgent
    instructions = models.TextField(blank=True)
    estimated_completion = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    worker_notes = models.TextField(blank=True)
    cancellation_reason = models.TextField(blank=True)

    assigned_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'assignments'
        ordering = ['-assigned_at']
        indexes = [
            models.Index(fields=['worker', 'status']),
            models.Index(fields=['report', 'status']),
        ]

    def __str__(self):
        return f'Assignment #{self.id}: Report #{self.report_id} → {self.worker}'

    @property
    def response_time_minutes(self):
        if self.completed_at:
            delta = self.completed_at - self.assigned_at
            return int(delta.total_seconds() / 60)
        return None


class EmergencyDispatch(models.Model):
    """
    Emergency dispatch records for critical incidents.
    Tracks which emergency units were dispatched.
    """
    report = models.ForeignKey(
        'reports.Report',
        on_delete=models.CASCADE,
        related_name='dispatches',
    )
    dispatch_type = models.CharField(max_length=50)  # ambulance, police, fire
    unit_name = models.CharField(max_length=200)
    unit_contact = models.CharField(max_length=50, blank=True)
    dispatched_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
    )
    dispatched_at = models.DateTimeField(auto_now_add=True)
    arrived_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'emergency_dispatches'
        ordering = ['-dispatched_at']

    def __str__(self):
        return f'{self.dispatch_type} dispatch for Report #{self.report_id}'
