import json
import multiprocessing
from multiprocessing import Manager
from collections import defaultdict
from .message_queue import RabbitMQ
from .utils import load_config
from .base import Base

MAX_PARRALLEL = 2

global_config = load_config()

class MessageCollector(Base):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.round: int = 0
        self.manager_process: multiprocessing.Process = None
        self.maintainer_process: multiprocessing.Process = None

        # self.message_count: int = 0      # 剩余未收到的消息数量
        self.manager = Manager()
        self.shared_data = self.manager.dict()
        self.shared_data["message_count"] = 0
        self.shared_data["message_sum"] = 0
        self.total_messages: int = 0     # 总消息数量
        self.message_dict: dict[str, str] = defaultdict()
        self.pbar = None                 # 进度条对象

        # For convenience, you can keep one RabbitMQ instance for each "role"
        # or reuse the same. Shown here as separate for clarity:
        self.rabbitmq_manager = RabbitMQ(**global_config['rabbitmq']['message_collector']['exchange'])
        self.rabbitmq_maintainer = RabbitMQ(**global_config['rabbitmq']['message_collector']['exchange'])

        # If needed, add queues for each connection. This depends on your config.
        # E.g. for manager:
        manager_queues = global_config['rabbitmq']['message_collector']['manager_queues']
        for q in manager_queues:
            self.rabbitmq_manager.add_queue(**q)

        # E.g. for maintainer:
        maintainer_queues = global_config['rabbitmq']['message_collector']['maintainer_queues']
        for q in maintainer_queues:
            self.rabbitmq_maintainer.add_queue(**q)

    def start(self):
        """Starts two processes:
           1) manager_process: handles messages from manager
           2) maintainer_process: handles responses from components
        """
        if self.manager_process or self.maintainer_process:
            self.warning("MessageCollector is already running.")
            return

        # Start the "manager" collector process
        self.manager_process = multiprocessing.Process(target=self._collect_manager)
        self.manager_process.start()
        self.info("ManagerProcess started.")

        # Start the "maintainer" collector process
        self.maintainer_process = multiprocessing.Process(target=self._collect_maintainer)
        self.maintainer_process.start()
        self.info("MaintainerProcess started.")

    def stop(self):
        """Stops both processes."""
        if self.manager_process:
            self.manager_process.terminate()
            self.manager_process.join()
            self.manager_process = None
            self.info("ManagerProcess stopped.")

        if self.maintainer_process:
            self.maintainer_process.terminate()
            self.maintainer_process.join()
            self.maintainer_process = None
            self.info("MaintainerProcess stopped.")

    def _collect_manager(self):
        """
        Subscribes to the manager-oriented queue (e.g. 'collector_manager').
        When a message from 'manager' is received, parse the tasks and call assign_tasks.
        """
        def callback_manager(channel, method, properties, body):
            sender = properties.headers.get('sender')
            body = body.decode('utf-8')
            # If the manager is sending messages to assign tasks:
            if sender == 'manager':
                self.round += 1
                # Body structure: [[component, message], [component, message], ...]
                informations = json.loads(body)
                components, messages = informations[0], informations[1]
                self.assign_tasks(components, messages)

            channel.basic_ack(delivery_tag=method.delivery_tag)

        try:
            # You might have something like queue='collector_manager'
            self.rabbitmq_manager.subscribe(queue='collector_manager', callback=callback_manager)
        except KeyboardInterrupt:
            self.warning("ManagerProcess connection closed.")
            exit(0)

    def _collect_maintainer(self):
        """
        Subscribes to the maintainer-oriented queue (e.g. 'collector_maintainer').
        When a component response is received, call response().
        """
        def callback_maintainer(channel, method, properties, body):
            sender = properties.headers.get('sender')
            body = body.decode('utf-8')
            # print(f"Received response from {sender}: {body}")
            # If this is from a component (or 'maintainer' in your logic), handle the response
            if sender != 'manager':
                self.response(sender, body)

            channel.basic_ack(delivery_tag=method.delivery_tag)

        try:
            # You might have something like queue='collector_maintainer'
            self.rabbitmq_maintainer.subscribe(queue='collector_maintainer', callback=callback_maintainer)
        except KeyboardInterrupt:
            self.warning("MaintainerProcess connection closed.")
            exit(0)

    def assign_tasks(self, components: list[str], messages: list[str]):
        """
        Called when the manager has provided new tasks for the components.
        This function tracks how many messages we expect back,
        and publishes each message to the relevant component queue.
        """
        self.total_messages = len(messages)
        self.shared_data["message_count"] = 0
        self.shared_data["message_sum"] = self.total_messages
        self.message_dict.clear()

        # Publish tasks to the service maintainer side
        project_rabbitmq = RabbitMQ(**global_config['rabbitmq']['service_maintainer']['exchange'])
        for component, message in zip(components, messages):
            self.shared_data["message_count"] += 1
            print(f"Assigning task to {component}: {message}")
            project_rabbitmq.publish(
                message=message,
                routing_keys=[component]
            )
            while self.shared_data["message_count"] >= MAX_PARRALLEL:
                import time
                time.sleep(5)

    def response(self, component: str, message: str):
        """
        Called when a response from a component is received.
        Decrements the message counter, updates the progress bar,
        and if all responses are collected, publishes them back to the manager.
        """
        self.shared_data["message_count"] -= 1
        self.shared_data["message_sum"] -= 1
        print(f"Received response from {component}: {message}")
        # print(f"Remaining Queue messages: {self.shared_data['message_count']}")
        print(f"Remaining Total messages: {self.shared_data['message_sum']}")

        # Store the response in our dictionary
        self.message_dict[component] = message

        # If we've collected all expected responses, send them back to manager
        if self.shared_data["message_sum"] == 0:
            response_message = "\n".join(list(self.message_dict.values()))
            project_rabbitmq = RabbitMQ(**global_config['rabbitmq']['manager']['exchange'])
            queues = global_config['rabbitmq']['manager']['queues']
            for queue in queues:
                project_rabbitmq.add_queue(**queue)

            project_rabbitmq.publish(
                message=response_message,
                routing_keys=['manager'],
            )