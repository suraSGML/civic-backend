"""Views for assignment management."""
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsAdminOrSuperAdmin, IsFieldWorker
from notifications.tasks import send_assignment_notification
from reports.models import Report
from .models import Assignment, AssignmentStatus, EmergencyDispatch
from .serializers import (
    AssignmentSerializer,
    AssignmentCreateSerializer,
    WorkerAssignmentUpdateSerializer,
    EmergencyDispatchSerializer,
)
from .utils import get_worker_suggestions, get_worker_performance_metrics


class AssignmentListCreateView(generics.ListCreateAPIView):
    """Admin: list all assignments or create a new one."""
    permission_classes = [IsAdminOrSuperAdmin]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return AssignmentCreateSerializer
        return AssignmentSerializer

    def get_queryset(self):
        return Assignment.objects.select_related(
            'report', 'worker', 'assigned_by'
        ).all()

    def perform_create(self, serializer):
        assignment = serializer.save()
        try:
            send_assignment_notification.delay(assignment.id)
        except Exception:
            pass


class AssignmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Admin: manage a specific assignment."""
    permission_classes = [IsAdminOrSuperAdmin]
    queryset = Assignment.objects.all()
    serializer_class = AssignmentSerializer


class WorkerAssignmentsView(generics.ListAPIView):
    """Field worker: view their own assignments."""
    serializer_class = AssignmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Assignment.objects.filter(
            worker=self.request.user
        ).select_related('report').order_by('-assigned_at')


class WorkerAssignmentUpdateView(generics.UpdateAPIView):
    """Field worker: update assignment status."""
    serializer_class = WorkerAssignmentUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Assignment.objects.filter(worker=self.request.user)

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)


class ReportAssignmentsView(generics.ListAPIView):
    """List all assignments for a specific report."""
    serializer_class = AssignmentSerializer
    permission_classes = [IsAdminOrSuperAdmin]

    def get_queryset(self):
        return Assignment.objects.filter(report_id=self.kwargs['report_id'])


class CancelAssignmentView(APIView):
    """Admin: cancel an assignment."""
    permission_classes = [IsAdminOrSuperAdmin]

    def post(self, request, pk):
        try:
            assignment = Assignment.objects.get(pk=pk)
        except Assignment.DoesNotExist:
            return Response({'error': 'Assignment not found.'}, status=404)

        assignment.status = AssignmentStatus.CANCELLED
        assignment.cancellation_reason = request.data.get('reason', '')
        assignment.save()

        # Revert report status
        from reports.models import ReportStatus
        assignment.report.status = ReportStatus.UNDER_REVIEW
        assignment.report.save()

        return Response({'message': 'Assignment cancelled.'})


class EmergencyDispatchListCreateView(generics.ListCreateAPIView):
    """Manage emergency dispatches."""
    serializer_class = EmergencyDispatchSerializer
    permission_classes = [IsAdminOrSuperAdmin]

    def get_queryset(self):
        return EmergencyDispatch.objects.select_related('report', 'dispatched_by').all()


class EmergencyDispatchDetailView(generics.RetrieveUpdateAPIView):
    """Update emergency dispatch (arrival, resolution times)."""
    serializer_class = EmergencyDispatchSerializer
    permission_classes = [IsAdminOrSuperAdmin]
    queryset = EmergencyDispatch.objects.all()


class WorkerSuggestionsView(APIView):
    """Get suggested workers for a report."""
    permission_classes = [IsAdminOrSuperAdmin]

    def get(self, request, report_id):
        try:
            report = Report.objects.get(pk=report_id)
        except Report.DoesNotExist:
            return Response({'error': 'Report not found.'}, status=404)

        suggestions = get_worker_suggestions(report, limit=5)
        return Response({
            'report_id': report_id,
            'category': report.category,
            'severity': report.severity,
            'suggestions': suggestions,
        })


class WorkerPerformanceView(APIView):
    """Get performance metrics for a worker."""
    permission_classes = [IsAdminOrSuperAdmin]

    def get(self, request, worker_id):
        from accounts.models import User
        try:
            worker = User.objects.get(pk=worker_id)
        except User.DoesNotExist:
            return Response({'error': 'Worker not found.'}, status=404)

        metrics = get_worker_performance_metrics(worker)
        return Response({
            'worker_id': worker_id,
            'name': worker.get_full_name(),
            'department': worker.department,
            'specialization': worker.specialization,
            **metrics,
        })
