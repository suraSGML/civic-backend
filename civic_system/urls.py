"""
Main URL configuration for Civic System
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

# Root endpoint
def root_view(request):
    return JsonResponse({
        'message': 'Civic System API',
        'version': '1.0.0',
        'docs': '/api/docs/',
        'api': '/api/v1/'
    })

api_v1_patterns = [
    path('health/', lambda request: JsonResponse({'status': 'ok', 'message': 'Backend is running'})),
    path('test-login/', lambda request: JsonResponse({'method': request.method, 'data': dict(request.POST) if request.method == 'POST' else {}})),
    path('auth/', include('accounts.urls')),
    path('reports/', include('reports.urls')),
    path('media/', include('media_files.urls')),
    path('assignments/', include('assignments.urls')),
    path('notifications/', include('notifications.urls')),
    path('analytics/', include('analytics.urls')),
]

urlpatterns = [
    path('', root_view, name='root'),
    path('admin/', admin.site.urls),
    path('api/v1/', include(api_v1_patterns)),

    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
