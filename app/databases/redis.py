import redis
from app.configs.settings import settings
from app.utils import get_logger
from redis.commands.json.path import Path

logger = get_logger(__name__)

class RedisDB:
    def __init__(self):
        self.client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, password=settings.REDIS_PWD)

    def set(self, key, value, ex=None):
        self.client.set(key, value, ex=ex)

    def get(self, key):
        return self.client.get(key)

    def jset(self, key, value, ex=None):
        self.client.json().set(key, Path.root_path(), value)
        if ex:
            self.client.expire(key, ex)

    def jget(self, key):
        return self.client.json().get(key, Path.root_path())

    def delete(self, key):
        self.client.delete(key)

redis_db = RedisDB()

