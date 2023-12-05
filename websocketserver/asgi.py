"""
ASGI config for websocketserver project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/howto/deployment/asgi/
"""

import os

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

from .ws.urls import websocket_urlpatterns
from .middleware import RouteNotFoundMiddleware

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'websocketserver.settings')

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": RouteNotFoundMiddleware(
        URLRouter(
            websocket_urlpatterns
        )
    )
})
