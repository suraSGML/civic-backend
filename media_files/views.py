"""Views for media file management."""
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser

from core.permissions import IsAdminOrSuperAdmin
from reports.models import Report
from .models import MediaFile
from .serializers import MediaFileSerializer, MediaFileUploadSerializer


class MediaFileUploadView(generics.CreateAPIView):
    """Upload media files for a specific report."""
    serializer_class = MediaFileUploadSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def perform_create(self, serializer):
        report_id = self.kwargs.get('report_id')
        try:
            report = Report.objects.get(pk=report_id)
        except Report.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound('Report not found.')

        # Check ownership or admin
        user = self.request.user
        if not user.can_manage_reports and report.reporter != user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('You can only upload media to your own reports.')

        serializer.save(
            report=report,
            uploaded_by=user,
            mime_type=getattr(self.request.data.get('file'), 'content_type', ''),
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        media = serializer.instance
        return Response(
            MediaFileSerializer(media, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


class MediaFileListView(generics.ListAPIView):
    """List all media files for a report."""
    serializer_class = MediaFileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return MediaFile.objects.filter(report_id=self.kwargs['report_id'])


class MediaFileDeleteView(generics.DestroyAPIView):
    """Delete a media file."""
    permission_classes = [permissions.IsAuthenticated]
    queryset = MediaFile.objects.all()

    def destroy(self, request, *args, **kwargs):
        media = self.get_object()
        if not request.user.can_manage_reports and media.uploaded_by != request.user:
            return Response({'error': 'Permission denied.'}, status=403)
        media.file.delete(save=False)
        media.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class FlagMediaView(generics.UpdateAPIView):
    """Admin: flag inappropriate media."""
    permission_classes = [IsAdminOrSuperAdmin]
    queryset = MediaFile.objects.all()

    def patch(self, request, *args, **kwargs):
        media = self.get_object()
        media.is_flagged = True
        media.flag_reason = request.data.get('reason', '')
        media.save()
        return Response({'message': 'Media flagged successfully.'})
