import redis
from django.conf import settings


r = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)
chat_limit = settings.CHAT_HISTORY_LIMIT
chat_key = settings.CHAT_REDIS_KEY


def add(value: str):
    """add messages to the redis history log"""
    r.lpush(chat_key, *[value])
    length = r.llen(chat_key)
    if length > chat_limit:
        r.rpop(chat_key)


def get(limit: int) -> list:
    """get last x messages from chat"""
    history = r.lrange(chat_key, 0, limit-1)
    return [v.decode('utf-8') for v in history]


def delete():
    """delete entire chat history hold in redis at the moment"""
    r.delete(chat_key)
