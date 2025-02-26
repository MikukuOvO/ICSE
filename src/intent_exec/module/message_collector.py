import json
import multiprocessing
from collections import defaultdict
from tqdm import tqdm  # 引入 tqdm 进度条
from .message_queue import RabbitMQ
from .utils import load_config
from .base import Base

global_config = load_config()

class MessageCollector(Base):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.round: int = 0
        self.process: multiprocessing.Process = None
        self.message_count: int = 0      # 剩余未收到的消息数量
        self.total_messages: int = 0     # 总消息数量
        self.message_dict: dict[str, str] = defaultdict()
        self.pbar = None                 # 进度条对象
        self.rabbitmq = RabbitMQ(**global_config['rabbitmq']['message_collector']['exchange'])
        queues = global_config['rabbitmq']['message_collector']['queues']
        for queue in queues:
            self.rabbitmq.add_queue(**queue)

    def start(self):
        if self.process:
            self.warning("MessageCollector is already running.")
            return
        self.process = multiprocessing.Process(target=self.__collect)
        self.process.start()
        self.info("MessageCollector started.")

    def stop(self):
        if not self.process:
            self.warning("MessageCollector is not running.")
            return
        self.process.terminate()
        self.process.join()
        self.process = None
        self.info("MessageCollector stopped.")

    def __collect(self):
        def callback(channel, method, properties, body):
            sender = properties.headers.get('sender')
            body = body.decode('utf-8')
            if sender == 'manager':
                self.round += 1
                # [[component, message], ...]
                informations = json.loads(body)
                components, messages = informations[0], informations[1]
                self.assign_tasks(components, messages)
            else:
                self.response(sender, body)
            channel.basic_ack(delivery_tag=method.delivery_tag)

        try:
            self.rabbitmq.subscribe(queue='collector', callback=callback)
        except KeyboardInterrupt:
            self.warning("Connection closed.")
            exit(0)

    def assign_tasks(self, components: list[str], messages: list[str]):
        self.total_messages = len(messages)
        self.message_count = self.total_messages
        self.message_dict.clear()
        # 初始化进度条，用于跟踪响应的进度
        self.pbar = tqdm(total=self.total_messages, desc="Receiving responses", unit="msg")
        # 假设 components 和 messages 数量一致
        project_rabbitmq = RabbitMQ(**global_config['rabbitmq']['service_maintainer']['exchange'])
        for component, message in zip(components, messages):
            project_rabbitmq.publish(
                message=message,
                routing_keys=[component]
            )

    def response(self, component: str, message: str):
        self.message_count -= 1
        # 更新进度条
        if self.pbar is not None:
            self.pbar.update(1)
        project_rabbitmq = RabbitMQ(**global_config['rabbitmq']['manager']['exchange'])
        queues = global_config['rabbitmq']['manager']['queues']
        for queue in queues:
            project_rabbitmq.add_queue(**queue)
        
        self.message_dict[component] = message
        if self.message_count == 0:
            # 所有响应收到后关闭进度条
            if self.pbar is not None:
                self.pbar.close()
                self.pbar = None
            response_message = "\n".join(list(self.message_dict.values()))
            project_rabbitmq.publish(
                message=response_message,
                routing_keys=['manager'],
            )
