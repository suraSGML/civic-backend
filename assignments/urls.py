"""URL patterns for assignments app."""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.AssignmentListCreateView.as_view(), name='assignment-list-create'),
    path('<int:pk>/', views.AssignmentDetailView.as_view(), name='assignment-detail'),
    path('<int:pk>/cancel/', views.CancelAssignmentView.as_view(), name='assignment-cancel'),
    path('my/', views.WorkerAssignmentsView.as_view(), name='my-assignments'),
    path('my/<int:pk>/', views.WorkerAssignmentUpdateView.as_view(), name='my-assignment-update'),
    path('report/<int:report_id>/', views.ReportAssignmentsView.as_view(), name='report-assignments'),
    path('report/<int:report_id>/suggestions/', views.WorkerSuggestionsView.as_view(), name='worker-suggestions'),
    path('worker/<int:worker_id>/performance/', views.WorkerPerformanceView.as_view(), name='worker-performance'),
    path('emergency/', views.EmergencyDispatchListCreateView.as_view(), name='emergency-dispatch'),
    path('emergency/<int:pk>/', views.EmergencyDispatchDetailView.as_view(), name='emergency-dispatch-detail'),
]
