"""URL patterns for analytics app."""
from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.DashboardSummaryView.as_view(), name='dashboard-summary'),
    path('by-category/', views.ReportsByCategoryView.as_view(), name='reports-by-category'),
    path('by-severity/', views.ReportsBySeverityView.as_view(), name='reports-by-severity'),
    path('trend/', views.ReportsTrendView.as_view(), name='reports-trend'),
    path('heatmap/', views.HeatmapDataView.as_view(), name='heatmap-data'),
    path('workers/', views.WorkerPerformanceView.as_view(), name='worker-performance'),
    path('high-risk-zones/', views.HighRiskZonesView.as_view(), name='high-risk-zones'),
    path('response-time/', views.ResponseTimeAnalyticsView.as_view(), name='response-time'),
]
