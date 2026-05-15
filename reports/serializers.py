"""
Serializers for the reports module.
"""
from rest_framework import serializers
from django.utils import timezone

from accounts.serializers import UserProfileSerializer
from .models import Report, ReportComment, StatusHistory, ReportUpvote, ReportStatus


class ReportCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    author_role = serializers.SerializerMethodField()

    class Meta:
        model = ReportComment
        fields = ['id', 'author', 'author_name', 'author_role',
                  'content', 'is_public', 'created_at']
        read_only_fields = ['id', 'author', 'created_at']

    def get_author_name(self, obj):
        return obj.author.get_full_name()

    def get_author_role(self, obj):
        return obj.author.role


class StatusHistorySerializer(serializers.ModelSerializer):
    changed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = StatusHistory
        fields = ['id', 'old_status', 'new_status', 'notes',
                  'changed_by_name', 'changed_at']

    def get_changed_by_name(self, obj):
        return obj.changed_by.get_full_name() if obj.changed_by else 'System'


class ReportListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""
    reporter_name = serializers.SerializerMethodField()
    media_count = serializers.SerializerMethodField()
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Report
        fields = [
            'id', 'title', 'category', 'category_display',
            'severity', 'severity_display', 'status', 'status_display',
            'latitude', 'longitude', 'address', 'city',
            'is_emergency', 'is_anonymous', 'upvote_count',
            'reporter_name', 'media_count', 'created_at',
        ]

    def get_reporter_name(self, obj):
        if obj.is_anonymous or not obj.reporter:
            return 'Anonymous'
        return obj.reporter.get_full_name()

    def get_media_count(self, obj):
        return obj.media_files.count()


class ReportDetailSerializer(serializers.ModelSerializer):
    """Full serializer for report detail views."""
    reporter = UserProfileSerializer(read_only=True)
    comments = serializers.SerializerMethodField()
    status_history = StatusHistorySerializer(many=True, read_only=True)
    media_files = serializers.SerializerMethodField()
    assignment = serializers.SerializerMethodField()
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    response_time = serializers.IntegerField(read_only=True)
    has_upvoted = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = [
            'id', 'reporter', 'title', 'description',
            'category', 'category_display', 'severity', 'severity_display',
            'status', 'status_display', 'latitude', 'longitude',
            'address', 'city', 'region', 'is_anonymous', 'is_emergency',
            'is_verified', 'upvote_count', 'has_upvoted',
            'admin_notes', 'rejection_reason', 'resolution_notes',
            'resolved_at', 'response_time', 'media_files',
            'comments', 'status_history', 'assignment',
            'created_at', 'updated_at',
        ]

    def get_comments(self, obj):
        request = self.context.get('request')
        qs = obj.comments.all()
        if request and not request.user.can_manage_reports:
            qs = qs.filter(is_public=True)
        return ReportCommentSerializer(qs, many=True).data

    def get_media_files(self, obj):
        from media_files.serializers import MediaFileSerializer
        return MediaFileSerializer(obj.media_files.all(), many=True).data

    def get_assignment(self, obj):
        assignment = obj.assignments.filter(
            status__in=['pending', 'in_progress']
        ).first()
        if assignment:
            from assignments.serializers import AssignmentSerializer
            return AssignmentSerializer(assignment).data
        return None

    def get_has_upvoted(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.upvotes.filter(user=request.user).exists()
        return False


class ReportCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = [
            'title', 'description', 'category', 'severity',
            'latitude', 'longitude', 'address', 'city', 'region',
            'is_anonymous',
        ]

    def validate_severity(self, value):
        from .models import SeverityLevel
        # Citizens can't set critical severity directly
        request = self.context.get('request')
        if request and request.user.is_citizen and value == SeverityLevel.CRITICAL:
            return SeverityLevel.HIGH
        return value

    def create(self, validated_data):
        validated_data['reporter'] = self.context['request'].user
        return super().create(validated_data)


class ReportUpdateSerializer(serializers.ModelSerializer):
    """For admin/authority status updates."""
    class Meta:
        model = Report
        fields = [
            'status', 'severity', 'admin_notes',
            'rejection_reason', 'resolution_notes',
        ]

    def update(self, instance, validated_data):
        old_status = instance.status
        new_status = validated_data.get('status', instance.status)

        instance = super().update(instance, validated_data)

        # Record status change
        if old_status != new_status:
            if new_status == ReportStatus.RESOLVED:
                instance.resolved_at = timezone.now()
                instance.save()
            StatusHistory.objects.create(
                report=instance,
                changed_by=self.context['request'].user,
                old_status=old_status,
                new_status=new_status,
                notes=validated_data.get('admin_notes', ''),
            )
        return instance


class MapReportSerializer(serializers.ModelSerializer):
    """Minimal serializer for map visualization."""
    class Meta:
        model = Report
        fields = [
            'id', 'title', 'category', 'severity', 'status',
            'latitude', 'longitude', 'is_emergency', 'created_at',
        ]
