"""URL patterns for reports app."""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.ReportListCreateView.as_view(), name='report-list-create'),
    path('<int:pk>/', views.ReportDetailView.as_view(), name='report-detail'),
    path('<int:pk>/status/', views.ReportStatusUpdateView.as_view(), name='report-status'),
    path('<int:pk>/upvote/', views.UpvoteReportView.as_view(), name='report-upvote'),
    path('<int:pk>/comments/', views.AddCommentView.as_view(), name='report-comments'),
    path('<int:report_id>/duplicates/', views.DuplicateDetectionView.as_view(), name='duplicate-detection'),
    path('my/', views.MyReportsView.as_view(), name='my-reports'),
    path('emergency/', views.EmergencyReportsView.as_view(), name='emergency-reports'),
    path('map/', views.MapReportsView.as_view(), name='map-reports'),
    path('nearby/', views.NearbyReportsView.as_view(), name='nearby-reports'),
    path('bulk/status/', views.BulkUpdateStatusView.as_view(), name='bulk-status-update'),
    path('bulk/export/', views.BulkExportView.as_view(), name='bulk-export'),
    path('bulk/merge/', views.MergeDuplicatesView.as_view(), name='merge-duplicates'),
    path('bulk/link/', views.LinkReportsView.as_view(), name='link-reports'),
]
