from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from django.conf import settings
from websocketserver.ws.minigames import minigame_broadcast_message, Minigame

headers = {"Access-Control-Allow-Origin": "*"}


class ApiBaseView(APIView):
    """
    view to get simple 200 back to check for server health
    """
    allowed_methods = {'GET'}
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(status=status.HTTP_200_OK, headers=headers)


class ApiVersionView(APIView):
    """
    view to get a server version
    """
    allowed_methods = {'GET'}
    permission_classes = [AllowAny]

    def get(self, request):
        data = {"api": "v1.0.1", "env": settings.HEAVENLAND_API_ENVIRONMENT, "desc": "Websocket Server Python"}
        return Response(status=status.HTTP_200_OK, headers=headers, data=data)


class WebhookView(APIView):
    """
    view to receive a webhook from the HL server
    """
    allowed_methods = {'GET'}
    permission_classes = [AllowAny]

    def get(self, request):
        minigame_broadcast_message()
        return Response(status=status.HTTP_200_OK, headers=headers)


class MinigameMockView(APIView):
    """
    view to respond with mocked data in structure of HL endpoint /api/gaming/events - for testing of UE server
    """
    allowed_methods = {'GET'}
    permission_classes = [AllowAny]

    def get(self, request):
        sgd = Minigame().__class__.shared_game_data
        players = []
        for p in sgd['players']:
            players.append({
                "id": p,
                "nickname": "default",
                "paragonAddress": "string"
            })
        setting = {
            "numberOfLaps": 20,
            "numberOfPlayers": 10,
            "map": "some map"
        }
        parameters = {
            "startsAt": sgd['start_at'],
            "registrationStartsAt": sgd['reg_start_at'],
            "registrationEndsAt": sgd['reg_end_at'],
            "currency": "HTO",
            "entryFee": 200,
            "rewardPool": 50000
        },
        data = {
            "id": sgd['id'],
            "miniGame": sgd['next_game'],
            "parameters": parameters,
            "settings": setting,
            "players": players,
            "results": None,
            "policyLink": "string"
        }
        resp = [data]
        return Response(resp, status=status.HTTP_200_OK, headers=headers)
