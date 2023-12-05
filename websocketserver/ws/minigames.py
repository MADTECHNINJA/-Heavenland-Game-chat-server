import logging
import threading
import schedule
import time
from uuid import uuid4
from datetime import datetime, timedelta
from random import randint
from django.conf import settings
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from channels.generic.websocket import JsonWebsocketConsumer
from .consumers import HLConsumer


logger = logging.getLogger(__name__)


def minigame_broadcast_message():
    """
    helper function that the webhook on `/api/webhook/minigame` uses to announce update on the HL API
    to the connected unreal engine server on this websocket connection
    """
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        settings.MINIGAME_GROUP, {
            "type": "broadcast",
            "json": {"info": "update"},
        }
    )


def run_continuously(interval=1):
    """
    background scheduler run function
    """
    cease_continuous_run = threading.Event()

    class ScheduleThread(threading.Thread):
        @classmethod
        def run(cls):
            while not cease_continuous_run.is_set():
                schedule.run_pending()
                time.sleep(interval)

    continuous_thread = ScheduleThread()
    continuous_thread.start()
    return cease_continuous_run


class Minigame:

    """
    mock class for development
    class that holds data about the scheduled minigames
    """

    boomer = False
    base_balance = 500
    players = {}
    period = 600  # second
    offset = 300  # second
    games = {}
    shared_game_data = {
        "id": "HLG-0",
        "enough_players": True,
        "next_game": "boomer",
        "start_at": 0,
        "reg_start_at": 0,
        "reg_end_at": 0,
        "players": []
    }

    def __init__(self, period: int = 600, offset: int = 300):
        self.period = period
        self.offset = offset
        # self.players = {key: self.base_balance for key in self.players}

    def update_online_players(self):
        """
        fetch online players using the HLConsumer -> this will return list of players connected to the in-game chat
        """
        st = HLConsumer().__class__.online_players
        self.players = dict((item, 0) for item in st)

    def next_game(self):
        """
        just a helper method
        """
        self.boomer = not self.boomer
        if self.boomer:
            return "boomer"
        else:
            return "speedspinner"

    def announce_next_game(self):
        """
        method to build data about the next minigame
        """
        self.update_online_players()
        no_players = len(self.players) if len(self.players) <= 10 else 10
        players = []
        available_players = list(self.players.keys())
        game_id = uuid4().hex
        self.games[game_id] = True
        for i in range(0, no_players):
            players.append({"id": available_players.pop(randint(0, len(available_players) - 1))})
        dt = datetime.utcnow() + timedelta(seconds=self.offset)
        data = {
            "id": game_id,
            "minigame": self.next_game(),
            "start_time": int(dt.timestamp()),
            "players_count": no_players,
            "players": players
        }
        return data

    def setup_next_game(self):
        """
        method used for mocking HL endpoint /api/gaming/events
        this will generate mocked data to build response for this endpoint
        -> used for development and testing of Unreal Engine server logic <-
        """
        self.update_online_players()
        no_players = len(self.players) if len(self.players) <= 10 else 10
        if no_players < 2:
            self.__class__.shared_game_data['enough_players'] = False
        else:
            self.__class__.shared_game_data['enough_players'] = True
        self.__class__.shared_game_data['next_game'] = self.next_game()
        self.__class__.shared_game_data['players'] = list(self.players.keys())
        try:
            game_id = int(self.__class__.shared_game_data['id'][4:])
        except ValueError:
            game_id = 0
        if game_id >= 3:
            game_id = 1
        else:
            game_id += 1
        self.__class__.shared_game_data['id'] = "HLG-" + str(game_id)

        reg_start_at = datetime.utcnow()
        reg_end_at = reg_start_at
        start_at = reg_start_at + timedelta(seconds=300)
        self.__class__.shared_game_data['start_at'] = int(start_at.timestamp())
        self.__class__.shared_game_data['reg_start_at'] = int(reg_start_at.timestamp())
        self.__class__.shared_game_data['reg_end_at'] = int(reg_end_at.timestamp())


def minigame_schedule(minigame: Minigame):
    """
    schedule a task which will generate a mocked minigame every x seconds
    the time between mocked minigames is given by the minigame.period attribute
    """
    schedule.clear()
    schedule.every(minigame.period).seconds.do(minigame_schedule, minigame)
    minigame.setup_next_game()
    minigame_broadcast_message()


class MinigameConsumer(JsonWebsocketConsumer):
    """
    main class to hold our logic of websocket - inheritance from the websocket library Channels base Consumer class
    every instance of this class is a connected client with active websocket connection

    this one is used for the UE servers to manage minigames
    """

    scheduler_thread = None
    minigame = None

    BASE_POOL_AMOUNT = 1000
    PLAYER_FEE = 100
    WIN_SPLIT = {
        1: 0.36,
        2: 0.26,
        3: 0.18,
        4: 0.12,
        5: 0.08
    }

    def start_scheduler(self, period: int, offset: int):
        """
        method to start a scheduler that will create a mocked minigames for testing
        """
        if self.__class__.scheduler_thread:
            self.__class__.scheduler_thread.set()
        self.__class__.minigame = Minigame(period, offset)
        minigame_schedule(minigame=self.minigame)
        self.__class__.scheduler_thread = run_continuously()
        self.send_group_message({"info": "scheduler is running"})

    def stop_scheduler(self):
        """
        method to stop a scheduler that is creating a mocked minigames for testing
        """
        if self.__class__.scheduler_thread:
            schedule.clear()
            self.__class__.scheduler_thread.set()
            self.send_group_message({"info": "scheduler is stopped"})

    def info_scheduler(self):
        """
        method that will respond to connected clients with info about scheduler that is creating a mocked minigames
        """
        jobs = schedule.get_jobs()
        logger.info(f"running jobs: {jobs}")
        if not self.__class__.minigame or len(jobs) < 1:
            self.send_group_message({"info": "scheduler is not running"})
        elif len(jobs) < 1:
            self.send_group_message({"info": "scheduler is not running"})
        else:
            data = {
                "info": "scheduler is running",
                "period": self.__class__.minigame.period,
                "offset": self.__class__.minigame.offset,
                # "games": dict(list(self.minigame.games.items())[:5])  # limit the amount of games to 100
            }
            self.send_group_message(data)

    def connect(self):
        """
        method that is called when new client is connected to the websocket endpoint
        """
        async_to_sync(self.channel_layer.group_add)(settings.MINIGAME_GROUP, self.channel_name)
        self.accept()

    def disconnect(self, close_code):
        """
        method that is called when client disconnects from the websocket endpoint
        """
        logger.warning(msg=f"user:{self.channel_name}|action:disconnected")
        async_to_sync(self.channel_layer.group_discard)(settings.MINIGAME_GROUP, self.channel_name)

    def receive_json(self, content, **kwargs):
        """
        method that will handle incoming json messages from the connected clients
        """
        if content.get('action') == 'game_end':
            self.process_end_game(content)
        elif content.get('action') == 'scheduler_start':
            self.start_scheduler(period=content.get('period', 600), offset=content.get('offset', 300))
        elif content.get('action') == 'scheduler_stop':
            self.stop_scheduler()
        elif content.get('action') == 'scheduler_info':
            self.info_scheduler()
        elif content.get('action') == 'online_players':
            if self.__class__.minigame:
                logger.info(self.__class__.minigame.players)

    def process_end_game(self, content: dict):
        """
        method to process incoming data about end of the minigame (results, etc) - just for UE server testing
        """
        minigame = self.__class__.minigame
        if not minigame:
            self.send_json({"error": "scheduler not running"})
            return
        if content.get('id') not in minigame.games.keys():
            self.send_json({"error": f"game with id {content.get('id')} not found in list of running games"})
            return

        data = content.get('leaderboard', [])
        ln = len(data)
        if ln < 1:
            self.send_json({"error": "leaderboard is empty"})

        total_pool = self.BASE_POOL_AMOUNT + ln * self.PLAYER_FEE
        for item in data:
            player_id = item.get('id')
            try:
                ps = item.pop('position')
            except KeyError:
                self.send_json({"error": f"position not found for player id {item.get('id')}"})
                return
            won = total_pool * self.WIN_SPLIT.get(ps, 0)
            try:
                minigame.players[player_id] += won
            except KeyError:
                self.send_json({"error": f"player id {player_id} not found in the pool of existing players"})
                return
            item['won'] = won
            item['balance'] = minigame.players[player_id]

        minigame.games.pop(content.get('id'))
        response = {
            "action": "balance_update",
            "data": data
        }
        self.send_group_message(response)

    def send_group_message(self, content, **kwargs):
        """
        method to handle logic before broadcasting a message to all connected clients
        """
        logger.warning(msg=f"message:{content.get('message')}")
        async_to_sync(self.channel_layer.group_send)(
            settings.MINIGAME_GROUP,
            {
                "type": "broadcast",
                "json": content,
            },
        )

    def broadcast(self, data):
        """
        method to broadcast JSON message to all connected clients
        """
        self.send_json(data['json'])
