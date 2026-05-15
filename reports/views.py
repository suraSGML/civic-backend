"""
Views for the reports module.
"""
import csv
import io
from django.db.models import Q, Count
from django.utils import timezone
from django.http import HttpResponse
from rest_framework import generics, status, permissions, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from core.permissions import IsAdminOrSuperAdmin, IsOwnerOrAdmin
from notifications.tasks import send_report_notification
from .models import (
    Report, ReportComment, ReportUpvote, StatusHistory,
    ReportStatus, SeverityLevel,
)
from .serializers import (
    ReportListSerializer, ReportDetailSerializer,
    ReportCreateSerializer, ReportUpdateSerializer,
    ReportCommentSerializer, MapReportSerializer,
)
from .filters import ReportFilter
from .exceptions import (
    InvalidStatusTransition, ReportNotFound, UnauthorizedStatusUpdate,
    InvalidBulkOperation,
)


class ReportListCreateView(generics.ListCreateAPIView):
    """
    GET: List reports (filtered by role).
    POST: Submit a new report.
    """
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ReportFilter
    search_fields = ['title', 'description', 'address']
    ordering_fields = ['created_at', 'severity', 'upvote_count']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ReportCreateSerializer
        return ReportListSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Report.objects.select_related('reporter').prefetch_related('media_files')

        if user.is_citizen:
            # Citizens see their own reports + public non-anonymous reports
            return qs.filter(
                Q(reporter=user) | Q(is_anonymous=False)
            )
        elif user.is_field_worker:
            # Workers see assigned reports
            return qs.filter(assignments__worker=user).distinct()
        else:
            # Admins see all
            return qs.all()

    def perform_create(self, serializer):
        report = serializer.save()
        # Trigger notifications asynchronously
        try:
            send_report_notification.delay(report.id, 'new_report')
        except Exception:
            pass  # Don't fail if Celery is not running


class ReportDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Get, update, or delete a specific report."""
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return ReportUpdateSerializer
        return ReportDetailSerializer

    def get_queryset(self):
        user = self.request.user
        if user.can_manage_reports:
            return Report.objects.all()
        return Report.objects.filter(
            Q(reporter=user) | Q(is_anonymous=False)
        )

    def update(self, request, *args, **kwargs):
        report = self.get_object()
        
        if not request.user.can_manage_reports:
            raise UnauthorizedStatusUpdate()
        
        new_status = request.data.get('status')
        if new_status and new_status != report.status:
            # Validate transition
            if not report.can_transition_to(new_status):
                raise InvalidStatusTransition(report.status, new_status)
            
            # Perform transition
            try:
                report.transition_to(
                    new_status,
                    changed_by=request.user,
                    notes=request.data.get('notes', '')
                )
                
                # Send notification
                try:
                    send_report_notification.delay(report.id, 'status_update')
                except Exception:
                    pass  # Don't fail if Celery is not running
                
            except ValueError as e:
                raise InvalidStatusTransition(report.status, new_status, str(e))
        
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        report = self.get_object()
        if not request.user.can_manage_reports and report.reporter != request.user:
            return Response({'error': 'Permission denied.'}, status=403)
        return super().destroy(request, *args, **kwargs)


class MyReportsView(generics.ListAPIView):
    """List the authenticated user's own reports."""
    serializer_class = ReportListSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = ReportFilter
    ordering = ['-created_at']

    def get_queryset(self):
        return Report.objects.filter(reporter=self.request.user)


class EmergencyReportsView(generics.ListAPIView):
    """List active emergency reports — for responders and admins."""
    serializer_class = ReportListSerializer
    permission_classes = [IsAdminOrSuperAdmin]

    def get_queryset(self):
        return Report.objects.filter(
            is_emergency=True,
            status__in=[ReportStatus.PENDING, ReportStatus.UNDER_REVIEW, ReportStatus.ASSIGNED],
        ).order_by('-created_at')


class MapReportsView(generics.ListAPIView):
    """Minimal report data for map visualization."""
    serializer_class = MapReportSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = ReportFilter
    pagination_class = None  # Return all points for the map

    def get_queryset(self):
        return Report.objects.filter(
            status__in=[
                ReportStatus.PENDING, ReportStatus.UNDER_REVIEW,
                ReportStatus.ASSIGNED, ReportStatus.IN_PROGRESS,
            ]
        )


class UpvoteReportView(APIView):
    """Toggle upvote on a report (community verification)."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            report = Report.objects.get(pk=pk)
        except Report.DoesNotExist:
            return Response({'error': 'Report not found.'}, status=404)

        upvote, created = ReportUpvote.objects.get_or_create(
            report=report, user=request.user
        )
        if not created:
            upvote.delete()
            report.upvote_count = max(0, report.upvote_count - 1)
            report.save()
            return Response({'upvoted': False, 'count': report.upvote_count})

        report.upvote_count += 1
        report.save()
        return Response({'upvoted': True, 'count': report.upvote_count})


class AddCommentView(generics.CreateAPIView):
    """Add a comment to a report."""
    serializer_class = ReportCommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        report = Report.objects.get(pk=self.kwargs['pk'])
        is_public = self.request.user.is_citizen  # Citizens always post public
        serializer.save(author=self.request.user, report=report, is_public=is_public)


class NearbyReportsView(APIView):
    """Find reports near a given GPS coordinate."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            lat = float(request.query_params.get('lat'))
            lng = float(request.query_params.get('lng'))
            radius_km = float(request.query_params.get('radius', 5))
        except (TypeError, ValueError):
            return Response({'error': 'lat, lng are required.'}, status=400)

        # Approximate bounding box (1 degree ≈ 111 km)
        delta = radius_km / 111.0
        reports = Report.objects.filter(
            latitude__range=(lat - delta, lat + delta),
            longitude__range=(lng - delta, lng + delta),
            status__in=[ReportStatus.PENDING, ReportStatus.IN_PROGRESS],
        )
        serializer = MapReportSerializer(reports, many=True)
        return Response(serializer.data)


class ReportStatusUpdateView(APIView):
    """Quick status update endpoint for workers."""
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        try:
            report = Report.objects.get(pk=pk)
        except Report.DoesNotExist:
            return Response({'error': 'Report not found.'}, status=404)

        new_status = request.data.get('status')
        notes = request.data.get('notes', '')

        if not new_status:
            return Response({'error': 'status is required.'}, status=400)

        # Workers can only update to in_progress or resolved
        if request.user.is_field_worker:
            allowed = [ReportStatus.IN_PROGRESS, ReportStatus.RESOLVED]
            if new_status not in allowed:
                return Response({'error': 'Workers can only set in_progress or resolved.'}, status=403)

        old_status = report.status
        report.status = new_status
        if new_status == ReportStatus.RESOLVED:
            report.resolved_at = timezone.now()
            report.resolution_notes = notes
        report.save()

        StatusHistory.objects.create(
            report=report,
            changed_by=request.user,
            old_status=old_status,
            new_status=new_status,
            notes=notes,
        )

        try:
            send_report_notification.delay(report.id, 'status_update')
        except Exception:
            pass

        return Response(ReportDetailSerializer(report, context={'request': request}).data)


class BulkUpdateStatusView(APIView):
    """Bulk update report statuses with validation."""
    permission_classes = [IsAdminOrSuperAdmin]

    def post(self, request):
        report_ids = request.data.get('report_ids', [])
        new_status = request.data.get('status')

        if not report_ids or not new_status:
            raise InvalidBulkOperation(
                'report_ids (list) and status (string) are required.'
            )

        if not isinstance(report_ids, list):
            raise InvalidBulkOperation('report_ids must be a list.')

        reports = Report.objects.filter(id__in=report_ids)
        
        if not reports.exists():
            raise ReportNotFound()
        
        results = {
            'updated': [],
            'failed': [],
            'total': len(report_ids),
        }

        for report in reports:
            if report.can_transition_to(new_status):
                try:
                    report.transition_to(
                        new_status,
                        changed_by=request.user,
                        notes=request.data.get('notes', ''),
                    )
                    results['updated'].append(report.id)
                    
                    # Send notification
                    try:
                        send_report_notification.delay(report.id, 'status_update')
                    except Exception:
                        pass
                except Exception as e:
                    results['failed'].append({
                        'id': report.id,
                        'reason': str(e),
                    })
            else:
                results['failed'].append({
                    'id': report.id,
                    'reason': f'Cannot transition from {report.status} to {new_status}',
                })

        return Response(results)


class BulkExportView(APIView):
    """Export multiple reports to CSV or PDF."""
    permission_classes = [IsAdminOrSuperAdmin]

    def post(self, request):
        report_ids = request.data.get('report_ids', [])
        export_format = request.data.get('format', 'csv').lower()

        if not report_ids:
            return Response({'error': 'report_ids is required.'}, status=400)

        if export_format not in ['csv', 'pdf']:
            return Response({'error': 'format must be csv or pdf.'}, status=400)

        reports = Report.objects.filter(id__in=report_ids).select_related('reporter')

        if export_format == 'csv':
            return self._export_csv(reports)
        else:
            return self._export_pdf(reports)

    def _export_csv(self, reports):
        """Export reports as CSV."""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            'ID', 'Title', 'Category', 'Severity', 'Status',
            'Reporter', 'City', 'Address', 'Created', 'Resolved',
            'Upvotes', 'Is Emergency'
        ])
        
        # Data rows
        for report in reports:
            writer.writerow([
                report.id,
                report.title,
                report.get_category_display(),
                report.get_severity_display(),
                report.get_status_display(),
                report.reporter.get_full_name() if report.reporter else 'Anonymous',
                report.city,
                report.address,
                report.created_at.strftime('%Y-%m-%d %H:%M'),
                report.resolved_at.strftime('%Y-%m-%d %H:%M') if report.resolved_at else '',
                report.upvote_count,
                'Yes' if report.is_emergency else 'No',
            ])
        
        # Create response
        response = HttpResponse(output.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="reports-{timezone.now().strftime("%Y%m%d-%H%M%S")}.csv"'
        return response

    def _export_pdf(self, reports):
        """Export reports as PDF."""
        try:
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
            from reportlab.lib import colors
        except ImportError:
            return Response(
                {'error': 'PDF export requires reportlab. Install with: pip install reportlab'},
                status=400
            )

        output = io.BytesIO()
        doc = SimpleDocTemplate(output, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#1f2937'),
            spaceAfter=12,
        )
        elements.append(Paragraph(f'Reports Export - {timezone.now().strftime("%Y-%m-%d")}', title_style))
        elements.append(Spacer(1, 0.3 * inch))
        
        # Table data
        data = [['ID', 'Title', 'Category', 'Status', 'City', 'Created']]
        for report in reports[:50]:  # Limit to 50 for PDF readability
            data.append([
                str(report.id),
                report.title[:30],
                report.get_category_display(),
                report.get_status_display(),
                report.city,
                report.created_at.strftime('%Y-%m-%d'),
            ])
        
        # Create table
        table = Table(data, colWidths=[0.6*inch, 2*inch, 1*inch, 1*inch, 1*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
        ]))
        
        elements.append(table)
        
        # Build PDF
        doc.build(elements)
        output.seek(0)
        
        response = HttpResponse(output.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="reports-{timezone.now().strftime("%Y%m%d-%H%M%S")}.pdf"'
        return response


class DuplicateDetectionView(APIView):
    """Find potential duplicate reports."""
    permission_classes = [IsAdminOrSuperAdmin]

    def get(self, request, report_id):
        try:
            report = Report.objects.get(pk=report_id)
        except Report.DoesNotExist:
            return Response({'error': 'Report not found.'}, status=404)

        from .duplicate_detection import find_potential_duplicates
        duplicates = find_potential_duplicates(report, threshold=0.65, limit=5)
        
        return Response({
            'report_id': report_id,
            'duplicates': duplicates,
            'count': len(duplicates),
        })


class MergeDuplicatesView(APIView):
    """Merge a duplicate report into the primary report."""
    permission_classes = [IsAdminOrSuperAdmin]

    def post(self, request):
        primary_id = request.data.get('primary_id')
        duplicate_id = request.data.get('duplicate_id')

        if not primary_id or not duplicate_id:
            return Response(
                {'error': 'primary_id and duplicate_id are required.'},
                status=400
            )

        from .duplicate_detection import merge_reports
        result = merge_reports(primary_id, duplicate_id, user=request.user)
        
        if not result.get('success'):
            return Response(result, status=400)
        
        return Response(result)


class LinkReportsView(APIView):
    """Link two related reports."""
    permission_classes = [IsAdminOrSuperAdmin]

    def post(self, request):
        report_id_1 = request.data.get('report_id_1')
        report_id_2 = request.data.get('report_id_2')

        if not report_id_1 or not report_id_2:
            return Response(
                {'error': 'report_id_1 and report_id_2 are required.'},
                status=400
            )

        from .duplicate_detection import link_reports
        result = link_reports(report_id_1, report_id_2)
        
        if not result.get('success'):
            return Response(result, status=400)
        
        return Response(result)
