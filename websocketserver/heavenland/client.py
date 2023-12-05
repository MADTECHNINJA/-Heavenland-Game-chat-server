import random

from websocketserver.heavenland.api import HeavenLandAPI
from websocketserver.heavenland.exceptions import JWTDecodeError


def game_login(username: str, password: str) -> dict:
    refresh_token, access_token, payload = HeavenLandAPI().game_login(username, password)
    user_id = payload.get('sub')
    return {
        "refresh_token": refresh_token,
        "access_token": access_token,
        "user_id": user_id
    }


def validate_heavenland_token(access_token: str) -> dict:
    return HeavenLandAPI().validate_token(access_token)


def get_nickname(user_id: str, access_token: str) -> dict:
    return HeavenLandAPI().get_account(user_id, access_token)
