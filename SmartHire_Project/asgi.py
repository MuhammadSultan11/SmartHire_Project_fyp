"""
ASGI config for SmartHire_Project project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import path
from candidate.consumers import ProgressConsumer
import candidate.routing  # Adjust if routing is elsewhere
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SmartHire_Project.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            candidate.routing.websocket_urlpatterns
        )
    ),
})