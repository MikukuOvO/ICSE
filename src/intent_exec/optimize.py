import os
import time
import json
import random
import subprocess
import signal
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

timeout = 2400  # 40 minutes total runtime
interval = 600  # 10 minutes between task triggers

def cleanup_resources(process, message_collector, manager_consumer, service_maintainer_consumers, rabbitmq=None):
    """Properly clean up all resources before exiting"""
    logger.info('Starting cleanup process...')
    
    # First stop all the consumers
    if message_collector:
        message_collector.stop()
    if manager_consumer:
        manager_consumer.stop()
    if service_maintainer_consumers:
        for consumer in service_maintainer_consumers:
            consumer.stop()
    
    # Close RabbitMQ connection if it exists
    if rabbitmq and hasattr(rabbitmq, 'connection') and rabbitmq.connection and rabbitmq.connection.is_open:
        try:
            if hasattr(rabbitmq, 'channel') and rabbitmq.channel and rabbitmq.channel.is_open:
                rabbitmq.channel.close()
            rabbitmq.connection.close()
            logger.info('RabbitMQ connection closed.')
        except Exception as e:
            logger.error(f'Error closing RabbitMQ connection: {str(e)}')
    
    # Export and sum up metrics
    try:
        csv_path = export_metrics()
        sum_up_metrics(csv_path)
        logger.info(f'Metrics exported to {csv_path}')
    except Exception as e:
        logger.error(f'Error exporting metrics: {str(e)}')
    
    # Stop traffic at the end
    try:
        if process:
            logger.info('Stopping the traffic...')
            end_traffic(process)
    except Exception as e:
        logger.error(f'Error stopping traffic: {str(e)}')
        # Force kill the process if needed
        try:
            os.kill(process.pid, signal.SIGTERM)
            logger.info(f'Force terminated process with PID {process.pid}')
        except Exception as e2:
            logger.error(f'Failed to kill process: {str(e2)}')
    
    logger.info('Cleanup complete.')

def main():
    process = None
    message_collector = None
    manager_consumer = None
    service_maintainer_consumers = []
    rabbitmq = None
    
    try:
        process = start_traffic()

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
        
        components = list_deployments(namespace, "src/conf/service_maintainers_optimize.yaml")
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
                task_name="optimize",
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
        
        # Task execution loop with 10-minute intervals
        start_time = time.time()
        end_time = start_time + timeout
        
        iteration = 0
        while time.time() < end_time:
            iteration += 1
            logger.info(f"Starting iteration {iteration}")
            try:
                # Check RabbitMQ connection and reconnect if needed
                if not rabbitmq.connection or not rabbitmq.connection.is_open:
                    logger.warning("RabbitMQ connection lost or not open. Reconnecting...")
                    rabbitmq = RabbitMQ(**global_config['rabbitmq']['manager']['exchange'])
                    for queue in queues:
                        rabbitmq.add_queue(**queue)
                
                # Publish the task
                logger.info(f'Triggering task: {task}')
                rabbitmq.publish(task, routing_keys=['manager'])
                logger.info("Task published successfully")
                
                # Wait for the next interval or until timeout is reached
                next_trigger = min(time.time() + interval, end_time)
                logger.info(f"Waiting until next trigger at {time.strftime('%H:%M:%S', time.localtime(next_trigger))}")
                while time.time() < next_trigger:
                    # Periodically check if connection is still alive
                    if (time.time() - next_trigger) % 60 < 5 and (not rabbitmq.connection or not rabbitmq.connection.is_open):
                        logger.warning("RabbitMQ connection lost during wait. Will reconnect on next iteration.")
                    time.sleep(5)  # Sleep in short intervals to allow for clean interrupt
            except Exception as e:
                logger.error(f"Error during task execution: {str(e)}")
                # Wait a bit before retrying
                time.sleep(30)
                
    except KeyboardInterrupt:
        logger.warning("Connection closed by user.")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
    finally:
        # Use the cleanup function to ensure all resources are properly closed
        cleanup_resources(process, message_collector, manager_consumer, service_maintainer_consumers, rabbitmq)

if __name__ == '__main__':
    main()