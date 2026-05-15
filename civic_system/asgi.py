"""
ASGI config for civic_system project.
Supports both HTTP and WebSocket connections via Django Channels.
"""
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'civic_system.settings')

django_asgi_app = get_asgi_application()

from core.routing import websocket_urlpatterns  # noqa: E402 - must be after django setup

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        )
    ),
})
