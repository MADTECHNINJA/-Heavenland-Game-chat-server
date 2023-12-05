import logging
import json
import time
from django.conf import settings
from jwt.exceptions import InvalidTokenError
from datetime import datetime
from channels.layers import get_channel_layer
from channels.generic.websocket import JsonWebsocketConsumer
from asgiref.sync import async_to_sync
from websocketserver.heavenland.client import game_login, get_nickname, validate_heavenland_token
from websocketserver.heavenland.exceptions import UnauthorizedError, HeavenlandAPIUnavailable, HeavenlandAPIError
from . import chat_history

logger = logging.getLogger(__name__)


def broadcast_message(user_id: str, data: dict):
    """
    function that can be imported to other files in the project that allows them to broadcast a message
    to all connected clients without making a new instance of the HLConsumer just for that case
    """
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        settings.CHAT_GROUP, {
            "type": "broadcast",
            "json": {
                "user_id": user_id,
                "data": data
            },
        }
    )


class HLConsumer(JsonWebsocketConsumer):
    """
    main class to hold our logic of websocket - inheritance from the websocket library Channels base Consumer class
    every instance of this class is a connected client with active websocket connection

    this one used for the in-game chat
    """

    authenticated = False
    nickname = None
    online_players = set()

    def receive_json(self, content, **kwargs):
        """
        function to handle incoming JSON messages from the connected client
        """
        # first check if user is already authenticated before checking for other requested actions
        if not self.authenticated:
            if content.get('action') == 'login':
                username = content.get('username')
                password = content.get('password')
                token = content.get('token')
                if not ((username and password) or token):
                    err_message = "username and password or token have to be provided with action of type login"
                    self.send_json({'error': err_message})
                self.authenticate(username, password, token)
            else:
                self.send_json({'error': "you need to authenticate first"})
        elif content.get('action') == 'message':
            self.send_group_message(self.channel_name, content, **kwargs)
        elif content.get('action') == 'history':
            self.get_chat_history(content.get('limit', 10))

    def disconnect(self, close_code):
        """
        function to handle tasks to do before client is disconnected
        """
        logger.warning(msg=f"user:{self.channel_name}|action:disconnected")
        try:
            self.__class__.online_players.remove(self.channel_name)
            logger.info(self.__class__.online_players)
        except KeyError:
            pass
        async_to_sync(self.channel_layer.group_discard)(settings.CHAT_GROUP, self.channel_name)

    def authenticate(self, username, password, token):
        """
        function to authenticate new connected client
        """
        if token:
            # if token is not None, then authenticate the client with token
            return self.authenticate_with_token(token)

        # try to log in the user given his username and password
        try:
            userdata = game_login(username, password)
        except UnauthorizedError:
            self.send_json({'error': "invalid credentials"})
            return
        except HeavenlandAPIUnavailable:
            self.send_json({'error': "heavenland authentication server is unavailable"})
            return
        except Exception as e:
            logger.exception(e)
            self.send_json({'error': "error occured during logging in"})
            return

        # load username and nickname of the player
        user_id = userdata.get('user_id')
        self.nickname = get_nickname(user_id, userdata['access_token']).get('nickname')
        if not user_id:
            self.send_json({'error': f"could not find user with username {username}"})
        self.authenticated = True

        # add the client to the channel layer - place to store connected clients
        async_to_sync(self.channel_layer.group_add)(settings.CHAT_GROUP, self.channel_name)
        self.channel_name = user_id
        logger.warning(msg=f"user:{self.channel_name}|action:connected")

        # respond with an info that the authentication was successful
        self.send_json({"info": "connected"})

    def authenticate_with_token(self, token):
        """
        function to authenticate new connected client with access token
        """
        # check for the token validity
        try:
            token_data = validate_heavenland_token(token)
        except InvalidTokenError as er:
            logger.exception(er)
            self.send_json({"error": "the access token is expired or invalid"})
            return
        except ValueError as er:
            logger.exception(er)
            self.send_json({"error": "error parsing the access token"})
            return

        # load username and nickname of the player
        user_id = token_data.get('sub')
        try:
            self.nickname = get_nickname(user_id, token).get('nickname')
        except HeavenlandAPIUnavailable as er:
            logger.exception(er)
            self.send_json({"error": f"Heavenland API request timeout, please try again"})
            return
        except HeavenlandAPIError as er:
            logger.exception(er)
            self.send_json({"error": f"{er.error_message}"})
            return
        if not user_id:
            self.send_json({'error': f"could not find user with given token (maybe token from different environment?)"})
        self.authenticated = True

        # add the client to the channel layer - place to store connected clients
        async_to_sync(self.channel_layer.group_add)(settings.CHAT_GROUP, self.channel_name)
        self.channel_name = user_id
        self.__class__.online_players.add(self.channel_name)
        logger.info(self.__class__.online_players)
        logger.warning(msg=f"user:{self.channel_name}|action:connected")

        # respond with an info that the authentication was successful
        self.send_json({"info": "connected"})

    def send_group_message(self, user_id, content, **kwargs):
        """
        function to handle logic before broadcasting message
        """
        # create the message and add timestamp to it
        message = {
            "user_id": user_id,
            "timestamp": int(time.mktime(datetime.utcnow().timetuple()))
        }
        content.pop('action')
        message.update(**content)

        # add nickname of the player and channel
        message['nickname'] = self.nickname
        if message.get('channel') is not None:
            message['channel'] = str(message['channel'])

        # log the message to chat history
        chat_history.add(json.dumps(message))
        logger.warning(msg=f"user:{user_id}|message:{content.get('message')}")

        # call the message broadcast function to send the message to all connected clients
        async_to_sync(self.channel_layer.group_send)(
            settings.CHAT_GROUP,
            {
                "type": "broadcast",
                "json": message,
            },
        )

    def broadcast(self, data):
        """
        broadcast a message to all connected clients with active websocket connection
        """
        self.send_json(data['json'])

    def get_chat_history(self, limit: int):
        """
        load X last messages from the chat history
        """
        messages = chat_history.get(limit)
        resp = {
            "history": [json.loads(message) for message in messages]
        }
        self.send_json(content=resp)
