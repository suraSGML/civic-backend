"""
Analytics views for the admin dashboard.
Provides statistics, charts, and performance metrics.
"""
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Avg, Q, F
from django.db.models.functions import TruncDate, TruncMonth
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions

from core.permissions import IsAdminOrSuperAdmin
from reports.models import Report, ReportStatus, ReportCategory, SeverityLevel
from accounts.models import User, UserRole
from assignments.models import Assignment


class DashboardSummaryView(APIView):
    """
    Main dashboard summary statistics.
    Returns key metrics for the admin overview.
    """
    permission_classes = [IsAdminOrSuperAdmin]

    def get(self, request):
        now = timezone.now()
        today = now.date()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        total_reports = Report.objects.count()
        reports_today = Report.objects.filter(created_at__date=today).count()
        reports_this_week = Report.objects.filter(created_at__gte=week_ago).count()
        reports_this_month = Report.objects.filter(created_at__gte=month_ago).count()

        pending = Report.objects.filter(status=ReportStatus.PENDING).count()
        in_progress = Report.objects.filter(status=ReportStatus.IN_PROGRESS).count()
        resolved = Report.objects.filter(status=ReportStatus.RESOLVED).count()
        rejected = Report.objects.filter(status=ReportStatus.REJECTED).count()
        duplicate = Report.objects.filter(status=ReportStatus.DUPLICATE).count()
        
        # Total completed = resolved + rejected + duplicate (all terminal states)
        completed = resolved + rejected + duplicate
        
        emergency_active = Report.objects.filter(
            is_emergency=True,
            status__in=[ReportStatus.PENDING, ReportStatus.UNDER_REVIEW, ReportStatus.ASSIGNED],
        ).count()

        # Average response time (minutes)
        avg_response = Report.objects.filter(
            resolved_at__isnull=False
        ).annotate(
            response_mins=F('resolved_at') - F('created_at')
        ).aggregate(avg=Avg('response_mins'))

        total_users = User.objects.filter(role=UserRole.CITIZEN).count()
        total_workers = User.objects.filter(role=UserRole.FIELD_WORKER).count()
        active_workers = Assignment.objects.filter(
            status__in=['pending', 'accepted', 'in_progress']
        ).values('worker').distinct().count()

        return Response({
            'reports': {
                'total': total_reports,
                'today': reports_today,
                'this_week': reports_this_week,
                'this_month': reports_this_month,
                'pending': pending,
                'in_progress': in_progress,
                'resolved': resolved,
                'rejected': rejected,
                'duplicate': duplicate,
                'completed': completed,
                'emergency_active': emergency_active,
            },
            'users': {
                'total_citizens': total_users,
                'total_workers': total_workers,
                'active_workers': active_workers,
            },
            'performance': {
                'resolution_rate': round((completed / total_reports * 100) if total_reports else 0, 1),
                'resolved_count': resolved,
                'rejected_count': rejected,
                'duplicate_count': duplicate,
            },
        })


class ReportsByCategoryView(APIView):
    """Reports grouped by category."""
    permission_classes = [IsAdminOrSuperAdmin]

    def get(self, request):
        data = Report.objects.values('category').annotate(
            count=Count('id'),
            resolved=Count('id', filter=Q(status=ReportStatus.RESOLVED)),
            pending=Count('id', filter=Q(status=ReportStatus.PENDING)),
        ).order_by('-count')

        result = []
        for item in data:
            result.append({
                'category': item['category'],
                'label': dict(ReportCategory.choices).get(item['category'], item['category']),
                'count': item['count'],
                'resolved': item['resolved'],
                'pending': item['pending'],
            })
        return Response(result)


class ReportsBySeverityView(APIView):
    """Reports grouped by severity."""
    permission_classes = [IsAdminOrSuperAdmin]

    def get(self, request):
        data = Report.objects.values('severity').annotate(count=Count('id')).order_by('severity')
        result = [
            {
                'severity': item['severity'],
                'label': dict(SeverityLevel.choices).get(item['severity']),
                'count': item['count'],
            }
            for item in data
        ]
        return Response(result)


class ReportsTrendView(APIView):
    """Daily report submission trend for the last 30 days."""
    permission_classes = [IsAdminOrSuperAdmin]

    def get(self, request):
        days = int(request.query_params.get('days', 30))
        since = timezone.now() - timedelta(days=days)

        data = Report.objects.filter(
            created_at__gte=since
        ).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            count=Count('id'),
            resolved=Count('id', filter=Q(status=ReportStatus.RESOLVED)),
            emergency=Count('id', filter=Q(is_emergency=True)),
        ).order_by('date')

        return Response(list(data))


class HeatmapDataView(APIView):
    """GPS coordinates for heatmap visualization."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        category = request.query_params.get('category')
        severity = request.query_params.get('severity')

        qs = Report.objects.filter(
            status__in=[
                ReportStatus.PENDING, ReportStatus.UNDER_REVIEW,
                ReportStatus.ASSIGNED, ReportStatus.IN_PROGRESS,
            ]
        )
        if category:
            qs = qs.filter(category=category)
        if severity:
            qs = qs.filter(severity=severity)

        data = qs.values('latitude', 'longitude', 'severity', 'category')
        return Response(list(data))


class WorkerPerformanceView(APIView):
    """Worker performance metrics."""
    permission_classes = [IsAdminOrSuperAdmin]

    def get(self, request):
        from assignments.models import AssignmentStatus
        workers = User.objects.filter(role=UserRole.FIELD_WORKER, is_active=True)
        result = []
        for worker in workers:
            assignments = worker.assignments.all()
            completed = assignments.filter(status=AssignmentStatus.COMPLETED)
            result.append({
                'worker_id': worker.id,
                'name': worker.get_full_name(),
                'department': worker.department,
                'total_assigned': assignments.count(),
                'completed': completed.count(),
                'in_progress': assignments.filter(status=AssignmentStatus.IN_PROGRESS).count(),
                'completion_rate': round(
                    (completed.count() / assignments.count() * 100)
                    if assignments.count() else 0, 1
                ),
            })
        result.sort(key=lambda x: x['completed'], reverse=True)
        return Response(result)


class HighRiskZonesView(APIView):
    """Identify high-risk zones based on report density."""
    permission_classes = [IsAdminOrSuperAdmin]

    def get(self, request):
        # Group by approximate grid (0.01 degree ≈ 1km)
        from django.db.models import FloatField
        from django.db.models.functions import Round

        data = Report.objects.filter(
            severity__in=[SeverityLevel.HIGH, SeverityLevel.CRITICAL]
        ).extra(
            select={
                'lat_grid': 'ROUND(CAST(latitude AS NUMERIC), 2)',
                'lng_grid': 'ROUND(CAST(longitude AS NUMERIC), 2)',
            }
        ).values('lat_grid', 'lng_grid').annotate(
            count=Count('id'),
            critical=Count('id', filter=Q(severity=SeverityLevel.CRITICAL)),
        ).filter(count__gte=2).order_by('-count')[:20]

        return Response(list(data))


class ResponseTimeAnalyticsView(APIView):
    """Response time analytics by category."""
    permission_classes = [IsAdminOrSuperAdmin]

    def get(self, request):
        from django.db.models import ExpressionWrapper, DurationField
        resolved = Report.objects.filter(resolved_at__isnull=False)
        data = resolved.values('category').annotate(
            count=Count('id'),
        ).order_by('category')

        result = []
        for item in data:
            cat_reports = resolved.filter(category=item['category'])
            total_mins = sum(
                r.response_time for r in cat_reports if r.response_time is not None
            )
            avg_mins = total_mins / item['count'] if item['count'] else 0
            result.append({
                'category': item['category'],
                'label': dict(ReportCategory.choices).get(item['category']),
                'count': item['count'],
                'avg_response_minutes': round(avg_mins, 1),
            })
        return Response(result)
