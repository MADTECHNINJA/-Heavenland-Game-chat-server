from django.urls import path
from . import views

urlpatterns = [
    path('', views.ApiBaseView.as_view()),
    path('version', views.ApiVersionView.as_view()),
    path('webhook/minigame', views.WebhookView.as_view()),
    path('gaming/events', views.MinigameMockView.as_view())
]
