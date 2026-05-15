"""
Report models for civic issue reporting.
Covers infrastructure, safety, and emergency incidents.
"""
from django.db import models
from django.conf import settings
from django.utils import timezone


class ReportCategory(models.TextChoices):
    # Infrastructure
    DAMAGED_ROAD = 'damaged_road', 'Damaged Road'
    BROKEN_STREETLIGHT = 'broken_streetlight', 'Broken Street Light'
    WATER_SUPPLY = 'water_supply', 'Water Supply Problem'
    ELECTRICITY = 'electricity', 'Electricity Outage'
    WASTE = 'waste', 'Waste Accumulation'
    SEWAGE = 'sewage', 'Sewage Problem'
    PUBLIC_PROPERTY = 'public_property', 'Damaged Public Property'
    # Safety & Emergency
    CRIME = 'crime', 'Crime Incident'
    ACCIDENT = 'accident', 'Traffic Accident'
    FIRE = 'fire', 'Fire Emergency'
    FLOOD = 'flood', 'Flood / Natural Disaster'
    MEDICAL = 'medical', 'Medical Emergency'
    # Other
    NOISE = 'noise', 'Noise Complaint'
    OTHER = 'other', 'Other'


class SeverityLevel(models.TextChoices):
    LOW = 'low', 'Low'
    MEDIUM = 'medium', 'Medium'
    HIGH = 'high', 'High'
    CRITICAL = 'critical', 'Critical'


class ReportStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    UNDER_REVIEW = 'under_review', 'Under Review'
    ASSIGNED = 'assigned', 'Assigned'
    IN_PROGRESS = 'in_progress', 'In Progress'
    RESOLVED = 'resolved', 'Resolved'
    REJECTED = 'rejected', 'Rejected'
    DUPLICATE = 'duplicate', 'Duplicate'


EMERGENCY_CATEGORIES = [
    ReportCategory.CRIME,
    ReportCategory.ACCIDENT,
    ReportCategory.FIRE,
    ReportCategory.FLOOD,
    ReportCategory.MEDICAL,
]


class Report(models.Model):
    """
    Core report model. Citizens submit reports about civic issues.
    """
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='reports',
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=50, choices=ReportCategory.choices, db_index=True)
    severity = models.CharField(
        max_length=20,
        choices=SeverityLevel.choices,
        default=SeverityLevel.MEDIUM,
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=ReportStatus.choices,
        default=ReportStatus.PENDING,
        db_index=True,
    )

    # Location
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    address = models.CharField(max_length=500, blank=True)
    city = models.CharField(max_length=100, default='Bahir Dar')
    region = models.CharField(max_length=100, default='Amhara')

    # Metadata
    is_anonymous = models.BooleanField(default=False)
    is_emergency = models.BooleanField(default=False, db_index=True)
    is_verified = models.BooleanField(default=False)
    is_duplicate = models.BooleanField(default=False)
    duplicate_of = models.ForeignKey(
        'self', null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='duplicates',
    )
    related_reports = models.ManyToManyField(
        'self',
        blank=True,
        symmetrical=True,
        related_name='related_to',
    )

    # Admin notes
    admin_notes = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)

    # Upvotes (community verification)
    upvote_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Valid status transitions
    VALID_TRANSITIONS = {
        ReportStatus.PENDING: [ReportStatus.UNDER_REVIEW, ReportStatus.REJECTED, ReportStatus.DUPLICATE],
        ReportStatus.UNDER_REVIEW: [ReportStatus.ASSIGNED, ReportStatus.REJECTED, ReportStatus.DUPLICATE],
        ReportStatus.ASSIGNED: [ReportStatus.IN_PROGRESS, ReportStatus.REJECTED],
        ReportStatus.IN_PROGRESS: [ReportStatus.RESOLVED, ReportStatus.REJECTED],
        ReportStatus.RESOLVED: [],  # Terminal state
        ReportStatus.REJECTED: [],  # Terminal state
        ReportStatus.DUPLICATE: [],  # Terminal state
    }

    class Meta:
        db_table = 'reports'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['category', 'status']),
            models.Index(fields=['latitude', 'longitude']),
            models.Index(fields=['is_emergency', 'status']),
            models.Index(fields=['created_at', 'severity']),
        ]

    def __str__(self):
        return f'[{self.category}] {self.title} - {self.status}'

    def save(self, *args, **kwargs):
        # Auto-flag emergencies
        if self.category in EMERGENCY_CATEGORIES:
            self.is_emergency = True
        if self.severity == SeverityLevel.CRITICAL:
            self.is_emergency = True
        super().save(*args, **kwargs)

    def can_transition_to(self, new_status):
        """Check if status transition is valid."""
        return new_status in self.VALID_TRANSITIONS.get(self.status, [])

    def transition_to(self, new_status, changed_by, notes=''):
        """Safely transition to new status with history tracking."""
        if not self.can_transition_to(new_status):
            raise ValueError(f"Cannot transition from {self.status} to {new_status}")
        
        old_status = self.status
        self.status = new_status
        
        # Set resolved_at if transitioning to resolved
        if new_status == ReportStatus.RESOLVED:
            self.resolved_at = timezone.now()
        
        self.save()
        
        # Record in history
        StatusHistory.objects.create(
            report=self,
            old_status=old_status,
            new_status=new_status,
            changed_by=changed_by,
            notes=notes,
        )
        
        return self

    @property
    def response_time(self):
        """Time from creation to resolution in minutes."""
        if self.resolved_at:
            delta = self.resolved_at - self.created_at
            return int(delta.total_seconds() / 60)
        return None


class ReportUpvote(models.Model):
    """Community verification - citizens can upvote reports to confirm them."""
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='upvotes')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'report_upvotes'
        unique_together = ['report', 'user']


class ReportComment(models.Model):
    """Comments on reports by authorities or workers."""
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    is_public = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'report_comments'
        ordering = ['created_at']

    def __str__(self):
        return f'Comment by {self.author} on Report #{self.report_id}'


class StatusHistory(models.Model):
    """Track all status changes for a report."""
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='status_history')
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
    )
    old_status = models.CharField(max_length=20, choices=ReportStatus.choices)
    new_status = models.CharField(max_length=20, choices=ReportStatus.choices)
    notes = models.TextField(blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'status_history'
        ordering = ['-changed_at']
