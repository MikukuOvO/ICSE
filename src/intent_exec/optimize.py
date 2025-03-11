import os
import time
import json
import random
import subprocess
from .module.utils import get_ancestor_path

from .module import (
    Logger,
    load_config, 
    ManagerConsumer,
    ServiceMaintainerConsumer,
    MessageCollector,
    RabbitMQ
)

from .agent import (
    ClusterManager,
    ServiceMaintainer
)

from ..utils.export_csv import export_metrics, sum_up_metrics

from .env.resource import inject
from .env.utils import list_deployments
from .env.traffic import start_traffic, end_traffic

logger = Logger(__file__, 'INFO')

global_config = load_config()

base_path = get_ancestor_path(2)

timeout = 1200

def main():
    process = start_traffic()
    # inject_info = inject()

    # Refresh the API
    subprocess.run(["bash", "scripts/ops/api.sh"])

    namespace = 'social-network'
    timestamp = time.strftime("%Y%m%d-%H%M%S")

    result_dir = os.path.join(
        base_path, 
        'results',
        namespace,
        timestamp
    )
    os.makedirs(result_dir, exist_ok=True) 
    execution_file_path = os.path.join(result_dir, 'logs')
    os.makedirs(execution_file_path, exist_ok=True) 
    
    components = list_deployments(namespace, "src/conf/service_maintainers.yaml")
    cluster_manager = ClusterManager._init_from_config(
        cache_seed=42,
        components=components
    )
    manager_consumer = ManagerConsumer(
        agent=cluster_manager,
        log_file_path=os.path.join(execution_file_path, 'manager.md')
    )

    agents = [
        ServiceMaintainer._init_from_config(
            service_name=component,
            cache_seed=random.randint(0, 100),
        )
        for component in components
    ]

    service_maintainer_consumers = [
        ServiceMaintainerConsumer(
            agent=agent,
            log_file_path=os.path.join(execution_file_path, f'{agent.name}.md')
        )
        for agent in agents
    ]

    message_collector = MessageCollector()
    message_collector.start()

    for service_maintainer_consumer in service_maintainer_consumers:
        service_maintainer_consumer.start()
    manager_consumer.start()

    logger.warning(f'Agent chat histories are available at: {execution_file_path}')

    rabbitmq = RabbitMQ(**global_config['rabbitmq']['manager']['exchange'])
    queues = global_config['rabbitmq']['manager']['queues']
    for queue in queues:
        rabbitmq.add_queue(**queue)

    task = f'{global_config["heartbeat"]["group_task_prefix"]}{global_config["heartbeat"]["optimization_task"]}'
    rabbitmq.publish(task, routing_keys=['manager'])

    # Task execution loop
    try:
        time.sleep(timeout)
    except KeyboardInterrupt:
        logger.warning("Connection closed by user.")
    finally:
        logger.info('Task execution complete.')
        message_collector.stop()
        manager_consumer.stop()
        for service_maintainer_consumer in service_maintainer_consumers:
            service_maintainer_consumer.stop()

    csv_path = export_metrics()
    sum_up_metrics(csv_path)
    logger.info('Stopping the task...')
    end_traffic(process)

if __name__ == '__main__':
    main()