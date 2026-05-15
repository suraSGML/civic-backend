"""URL patterns for notifications app."""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.NotificationListView.as_view(), name='notification-list'),
    path('unread-count/', views.UnreadCountView.as_view(), name='unread-count'),
    path('mark-all-read/', views.MarkAllReadView.as_view(), name='mark-all-read'),
    path('<int:pk>/read/', views.MarkNotificationReadView.as_view(), name='mark-read'),
    path('preferences/', views.NotificationPreferenceView.as_view(), name='notification-preferences'),
]
