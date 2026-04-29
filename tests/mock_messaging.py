"""
Mock messaging module for testing without external dependencies
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class RocketMQConfig:
    """RocketMQ 配置"""
    name_server: str = "localhost:9876"
    producer_group: str = "ai_novels_producer"


class BaseProducer:
    """Base producer class"""
    def connect(self) -> bool:
        return True

    def is_connected(self) -> bool:
        return True

    def send_sync(self, topic: str, message: Dict, tags: str = None) -> Dict:
        return {"status": "sent", "topic": topic}

    def close(self):
        pass


class RocketMQProducer(BaseProducer):
    """Mock RocketMQ Producer"""
    def __init__(self, config: RocketMQConfig):
        self.config = config
        self._connected = True

    def connect(self) -> bool:
        self._connected = True
        return True

    def is_connected(self) -> bool:
        return self._connected

    def send_sync(self, topic: str, message: Dict, tags: str = None) -> Dict:
        return {"status": "sent", "topic": topic, "message_id": "mock_id"}

    def close(self):
        self._connected = False


@dataclass
class ConsumerConfig:
    """Consumer 配置"""
    name_server: str = "localhost:9876"
    consumer_group: str = "ai_novels_consumer"
    topic: str = "ai_novels_queue"
    max_concurrency: int = 5


class BaseConsumer:
    """Base consumer class"""
    def connect(self) -> bool:
        return True

    def subscribe(self, handler):
        pass

    def start(self):
        pass

    def stop(self):
        pass

    def is_connected(self) -> bool:
        return True

    def health_check(self) -> Dict:
        return {"status": "healthy"}


class RocketMQConsumer(BaseConsumer):
    """Mock RocketMQ Consumer"""
    def __init__(self, config: ConsumerConfig):
        self.config = config
        self._connected = True

    def connect(self) -> bool:
        self._connected = True
        return True

    def subscribe(self, handler):
        pass

    def start(self):
        pass

    def stop(self):
        pass

    def is_connected(self) -> bool:
        return self._connected

    def health_check(self) -> Dict:
        return {"status": "healthy"}
