"""Serializers for assignments."""
from rest_framework import serializers
from django.utils import timezone

from .models import Assignment, AssignmentStatus, EmergencyDispatch


class AssignmentSerializer(serializers.ModelSerializer):
    worker_name = serializers.SerializerMethodField()
    assigned_by_name = serializers.SerializerMethodField()
    report_title = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Assignment
        fields = [
            'id', 'report', 'report_title', 'worker', 'worker_name',
            'assigned_by', 'assigned_by_name', 'status', 'status_display',
            'priority', 'instructions', 'estimated_completion',
            'completed_at', 'worker_notes', 'cancellation_reason',
            'assigned_at', 'updated_at',
        ]
        read_only_fields = ['id', 'assigned_by', 'assigned_at', 'updated_at']

    def get_worker_name(self, obj):
        return obj.worker.get_full_name() if obj.worker else None

    def get_assigned_by_name(self, obj):
        return obj.assigned_by.get_full_name() if obj.assigned_by else None

    def get_report_title(self, obj):
        return obj.report.title if obj.report else None


class AssignmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assignment
        fields = ['report', 'worker', 'priority', 'instructions', 'estimated_completion']

    def validate(self, attrs):
        report = attrs.get('report')
        worker = attrs.get('worker')

        # Check worker role
        if not worker.is_field_worker:
            raise serializers.ValidationError({'worker': 'User must be a field worker.'})

        # Check for existing active assignment
        existing = Assignment.objects.filter(
            report=report,
            status__in=[AssignmentStatus.PENDING, AssignmentStatus.ACCEPTED,
                        AssignmentStatus.IN_PROGRESS],
        ).exists()
        if existing:
            raise serializers.ValidationError(
                {'report': 'This report already has an active assignment.'}
            )
        return attrs

    def create(self, validated_data):
        validated_data['assigned_by'] = self.context['request'].user
        assignment = super().create(validated_data)

        # Update report status
        from reports.models import ReportStatus
        assignment.report.status = ReportStatus.ASSIGNED
        assignment.report.save()
        return assignment


class WorkerAssignmentUpdateSerializer(serializers.ModelSerializer):
    """Workers update their own assignment status."""
    class Meta:
        model = Assignment
        fields = ['status', 'worker_notes']

    def validate_status(self, value):
        allowed = [AssignmentStatus.ACCEPTED, AssignmentStatus.IN_PROGRESS,
                   AssignmentStatus.COMPLETED]
        if value not in allowed:
            raise serializers.ValidationError(
                f'Workers can only set: {", ".join(allowed)}'
            )
        return value

    def update(self, instance, validated_data):
        new_status = validated_data.get('status', instance.status)
        if new_status == AssignmentStatus.COMPLETED:
            validated_data['completed_at'] = timezone.now()

            # Update report status
            from reports.models import ReportStatus
            instance.report.status = ReportStatus.IN_PROGRESS
            instance.report.save()

        return super().update(instance, validated_data)


class EmergencyDispatchSerializer(serializers.ModelSerializer):
    dispatched_by_name = serializers.SerializerMethodField()

    class Meta:
        model = EmergencyDispatch
        fields = [
            'id', 'report', 'dispatch_type', 'unit_name', 'unit_contact',
            'dispatched_by', 'dispatched_by_name', 'dispatched_at',
            'arrived_at', 'resolved_at', 'notes',
        ]
        read_only_fields = ['id', 'dispatched_by', 'dispatched_at']

    def get_dispatched_by_name(self, obj):
        return obj.dispatched_by.get_full_name() if obj.dispatched_by else None

    def create(self, validated_data):
        validated_data['dispatched_by'] = self.context['request'].user
        return super().create(validated_data)
