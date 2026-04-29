"""
RocketMQ Producer 测试

测试覆盖:
- ProducerConfig 配置类
- RocketMQProducer 生产者核心功能
- 消息创建与发送
- Mock模式行为验证
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.deepnovel.messaging.rocketmq_producer import (
    ProducerConfig, RocketMQProducer, BaseProducer,
    NovelGenerationMessage, notifyMessage
)


class TestProducerConfig:
    """ProducerConfig 配置类测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = ProducerConfig()
        assert config.group_name == "ai_novels_producer"
        assert config.name_server == "localhost:9876"
        assert config.max_message_size == 1048576
        assert config.send_message_timeout_ms == 3000
        assert config.retry_times_when_send_failed == 2

    def test_custom_config(self):
        """测试自定义配置"""
        config = ProducerConfig(
            group_name="test_group",
            name_server="test:9876",
            max_message_size=2048
        )
        assert config.group_name == "test_group"
        assert config.name_server == "test:9876"
        assert config.max_message_size == 2048

    def test_from_config_dict(self):
        """测试从字典创建配置"""
        config_dict = {
            "group_name": "dict_group",
            "name_server": "dict:9876",
            "access_key": "test_key"
        }
        config = ProducerConfig.from_config(config_dict)
        assert config.group_name == "dict_group"
        assert config.name_server == "dict:9876"
        assert config.access_key == "test_key"


class TestRocketMQProducerInit:
    """RocketMQProducer 初始化测试"""

    def test_init_default_config(self):
        """测试默认配置初始化"""
        producer = RocketMQProducer()
        assert producer._config is not None
        assert producer._config.group_name == "ai_novels_producer"
        assert producer._is_mock == True  # 无RocketMQ库时为mock模式

    def test_init_with_config_object(self):
        """测试使用配置对象初始化"""
        config = ProducerConfig(group_name="custom_group")
        producer = RocketMQProducer(config=config)
        assert producer._config.group_name == "custom_group"

    def test_init_with_kwargs(self):
        """测试使用kwargs初始化"""
        producer = RocketMQProducer(group_name="kwarg_group", name_server="kwarg:9876")
        assert producer._config.group_name == "kwarg_group"
        assert producer._config.name_server == "kwarg:9876"

    def test_init_mock_mode(self):
        """测试Mock模式初始化"""
        producer = RocketMQProducer()
        assert producer._is_mock == True


class TestRocketMQProducerConnection:
    """RocketMQProducer 连接管理测试"""

    def test_connect_mock_mode(self):
        """测试Mock模式连接"""
        producer = RocketMQProducer()
        assert producer.connect() == True
        assert producer.is_connected() == True

    def test_disconnect_mock_mode(self):
        """测试Mock模式断开连接"""
        producer = RocketMQProducer()
        producer.connect()
        assert producer.disconnect() == True
        assert producer.is_connected() == False

    def test_close_alias(self):
        """测试close是disconnect的别名"""
        producer = RocketMQProducer()
        producer.connect()
        assert producer.close() == True
        assert producer.is_connected() == False


class TestRocketMQProducerHealthCheck:
    """RocketMQProducer 健康检查测试"""

    def test_health_check_connected(self):
        """测试已连接状态的健康检查"""
        producer = RocketMQProducer()
        producer.connect()
        health = producer.health_check()
        assert health["status"] == "healthy"
        assert health["mode"] == "mock"
        assert "producer_group" in health["details"]

    def test_health_check_disconnected(self):
        """测试未连接状态的健康检查"""
        producer = RocketMQProducer()
        health = producer.health_check()
        assert health["status"] == "unhealthy"

    def test_test_connection(self):
        """测试test_connection方法"""
        producer = RocketMQProducer()
        assert producer.test_connection() == False  # 未连接
        producer.connect()
        assert producer.test_connection() == True  # 已连接


class TestRocketMQProducerSend:
    """RocketMQProducer 消息发送测试"""

    def test_send_sync_mock(self):
        """测试Mock模式同步发送"""
        producer = RocketMQProducer()
        message = {"data": "test"}
        result = producer.send_sync("test_topic", message, "test_tag")
        assert result is not None
        assert result["status"] == "sent"
        assert result["topic"] == "test_topic"
        assert "message_id" in result

    def test_send_mock(self):
        """测试通用send方法"""
        producer = RocketMQProducer()
        message = {"data": "test"}
        result = producer.send("test_topic", message, "test_tag", "sync")
        assert result is not None
        assert result["status"] == "sent"

    def test_send_async_mock(self):
        """测试Mock模式异步发送"""
        producer = RocketMQProducer()
        message = {"data": "test"}
        callback_called = [False]
        
        def callback(result, error):
            callback_called[0] = True
        
        result = producer.send_async("test_topic", message, "test_tag", callback)
        assert result == True

    def test_send_one_way_mock(self):
        """测试Mock模式单向发送"""
        producer = RocketMQProducer()
        message = {"data": "test"}
        result = producer.send_one_way("test_topic", message, "test_tag")
        assert result == True

    def test_send_without_connection(self):
        """测试未连接时发送"""
        producer = RocketMQProducer()
        # Mock模式会自动连接
        message = {"data": "test"}
        result = producer.send_sync("test_topic", message)
        assert result is not None


class TestRocketMQProducerBatch:
    """RocketMQProducer 批量发送测试"""

    def test_send_batch(self):
        """测试批量发送"""
        producer = RocketMQProducer()
        messages = [
            {"id": 1, "data": "msg1"},
            {"id": 2, "data": "msg2"},
            {"id": 3, "data": "msg3"}
        ]
        results = producer.send_batch("test_topic", messages, "batch_tag")
        assert len(results) == 3
        for result in results:
            assert result["status"] == "sent"


class TestRocketMQProducerAdvanced:
    """RocketMQProducer 高级功能测试"""

    def test_send_delayed_mock(self):
        """测试Mock模式延迟发送"""
        producer = RocketMQProducer()
        message = {"data": "test"}
        result = producer.send_delayed("test_topic", message, delay_level=2)
        assert result is not None
        assert result["status"] == "sent"
        assert result["delay_level"] == 2

    def test_send_orderly_mock(self):
        """测试Mock模式有序发送"""
        producer = RocketMQProducer()
        message = {"data": "test"}
        result = producer.send_orderly("test_topic", message, shard_key="user_123")
        assert result is not None
        assert result["status"] == "sent"
        assert result["shard_key"] == "user_123"


class TestNovelGenerationMessage:
    """NovelGenerationMessage 消息工厂测试"""

    def test_create_task(self):
        """测试创建生成任务消息"""
        config = {"genre": "fantasy", "chapters": 10}
        message = NovelGenerationMessage.create_task(
            task_id="task_001",
            user_id="user_001",
            config=config
        )
        assert message["message_type"] == "generation_task"
        assert message["task_id"] == "task_001"
        assert message["user_id"] == "user_001"
        assert message["action"] == "create"
        assert message["config"] == config
        assert "timestamp" in message

    def test_update_task(self):
        """测试创建任务更新消息"""
        message = NovelGenerationMessage.update_task(
            task_id="task_001",
            status="running",
            progress=0.5,
            error=None
        )
        assert message["message_type"] == "generation_task_update"
        assert message["task_id"] == "task_001"
        assert message["status"] == "running"
        assert message["progress"] == 0.5
        assert "timestamp" in message

    def test_generate_chapter(self):
        """测试创建章节生成消息"""
        context = {"outline": "chapter outline"}
        message = NovelGenerationMessage.generate_chapter(
            task_id="task_001",
            chapter_id="ch_001",
            outline_id="outline_001",
            context=context
        )
        assert message["message_type"] == "generate_chapter"
        assert message["task_id"] == "task_001"
        assert message["chapter_id"] == "ch_001"
        assert message["context"] == context


class TestNotifyMessage:
    """notifyMessage 消息工厂测试"""

    def test_create_notification(self):
        """测试创建通知消息"""
        message = notifyMessage.create(
            msg_type="info",
            title="Test Title",
            content="Test Content",
            recipients=["user1", "user2"]
        )
        assert message["message_type"] == "notification"
        assert message["notify_type"] == "info"
        assert message["title"] == "Test Title"
        assert message["content"] == "Test Content"
        assert message["recipients"] == ["user1", "user2"]
        assert "timestamp" in message


class TestBaseProducerAbstract:
    """BaseProducer 抽象基类测试"""

    def test_base_producer_is_abstract(self):
        """测试BaseProducer是抽象类"""
        with pytest.raises(TypeError):
            BaseProducer()

    def test_base_producer_subclass_must_implement(self):
        """测试子类必须实现抽象方法"""
        class IncompleteProducer(BaseProducer):
            pass
        
        with pytest.raises(TypeError):
            IncompleteProducer()
