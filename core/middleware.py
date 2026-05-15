"""
Audit logging middleware and database health check.
Records all API actions for security and compliance.
"""
import json
import logging
from django.utils import timezone
from django.db import connection
from django.db.utils import OperationalError

logger = logging.getLogger('civic_system')


class DatabaseHealthCheckMiddleware:
    """
    Checks database connection health and reconnects if needed.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            # Test database connection
            connection.ensure_connection()
        except OperationalError as e:
            logger.error(f"Database connection error: {e}")
            # Close and reconnect
            connection.close()
            try:
                connection.ensure_connection()
            except Exception as e2:
                logger.error(f"Failed to reconnect to database: {e2}")
        
        response = self.get_response(request)
        return response


class AuditLogMiddleware:
    """
    Logs all authenticated API requests for audit trail.
    Stores: user, action, endpoint, IP, timestamp.
    """
    EXCLUDED_PATHS = ['/api/schema/', '/api/docs/', '/static/', '/media/']

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Only log API calls from authenticated users
        if (
            request.path.startswith('/api/') and
            hasattr(request, 'user') and
            request.user.is_authenticated and
            not any(request.path.startswith(p) for p in self.EXCLUDED_PATHS) and
            request.method in ['POST', 'PUT', 'PATCH', 'DELETE']
        ):
            self._log_action(request, response)

        return response

    def _log_action(self, request, response):
        try:
            from core.models import AuditLog
            AuditLog.objects.create(
                user=request.user,
                action=f'{request.method} {request.path}',
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                status_code=response.status_code,
                extra_data={
                    'query_params': dict(request.GET),
                },
            )
        except Exception as e:
            logger.warning(f'Audit log failed: {e}')

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')
