from django.urls import re_path

from . import consumers, minigames

websocket_urlpatterns = [
    re_path(r'chat$', consumers.HLConsumer.as_asgi()),
    re_path(r'minigame$', minigames.MinigameConsumer.as_asgi()),
]