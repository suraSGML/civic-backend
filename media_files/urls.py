"""URL patterns for media_files app."""
from django.urls import path
from . import views

urlpatterns = [
    path('reports/<int:report_id>/upload/', views.MediaFileUploadView.as_view(), name='media-upload'),
    path('reports/<int:report_id>/', views.MediaFileListView.as_view(), name='media-list'),
    path('<int:pk>/', views.MediaFileDeleteView.as_view(), name='media-delete'),
    path('<int:pk>/flag/', views.FlagMediaView.as_view(), name='media-flag'),
]
