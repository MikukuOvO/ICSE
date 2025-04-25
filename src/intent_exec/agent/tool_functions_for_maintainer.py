# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
from autogen.coding.func_with_reqs import with_requirements, ImportFromModule
from typing import Literal

def query_prometheus(promQL: str, **kwargs) -> list:
    """
    This function is used to query prometheus with the given promQL.
    - param promQL: str, the promQL to be executed
    - param kwargs: dict, parameters to be passed to the query, must contain one of the following: (start_time, end_time), duration
    - return: list, result of the query

    Note: 
    - ALWAYS call print() to report the result so that planner can get the result.
    - ALWAYS call query_prometheus with full parameters, including promQL, duration and step. (Shown as example)

    Example: 
    >>> from src.agent.tool_functions_for_maintainer import query_prometheus
    >>> promQL = '<metric_name>{<label_selector>}'
    >>> result = query_prometheus(promQL=promQL, duration='?min', step='?s')
    >>> print(result) # output the result so that planner can get it.
    [['2024-06-20 02:17:20', 0.0], ['2024-06-20 02:18:20', 0.0], ['2024-06-20 02:19:20', 0.0]], ...
    """
    from intent_exec.module.prometheus_client import PrometheusClient
    prometheus_client = PrometheusClient()
    result: list[list[str, int]] = prometheus_client.query_range(promQL, **kwargs)
    return result

@with_requirements(python_packages=['Literal'], global_imports=[ImportFromModule('typing', 'Literal')])
def report_result(component: str, message: str, message_type: Literal['ISSUE', 'RESPONSE']) -> str:
    """
    This function can help you send a message to the manager.
    - param component: str, the component name
    - param message: str, the message to be reported
    - param type: str, the type of the message, use 'ISSUE' for HEARTBEAT and 'RESPONSE' for TASK

    return: str, the result of the operation

    Note: ALWAYS call print() to report the result so that planner can get the result.

    Example:
    >>> from intent_exec.agent.tool_functions_for_maintainer import report_result
    >>> component = 'catalogue'
    >>> message = 'The task is completed.'
    >>> message_type = 'RESPONSE'
    >>> result = report_result(component=component, message=messages, message_type=message_type)
    >>> print(result) # output the result so that planner can get it.
    Message sent to manager.
    """
    from intent_exec.module import RabbitMQ, load_config

    global_config = load_config()

    queues = global_config['rabbitmq']['message_collector']['maintainer_queues']
    rabbitmq = RabbitMQ(**global_config['rabbitmq']['message_collector']['exchange'])
    for queue in queues:
            rabbitmq.add_queue(**queue)

    if message_type == 'ISSUE':
        message = f'ISSUE from component {component}: \n {message}'
    elif message_type == 'RESPONSE':
        message = f'RESPONSE from component {component}: \n {message}'
    else:
        raise ValueError('Invalid message type.')

    rabbitmq.publish(
        message=message,
        routing_keys=['collector_maintainer'],
        headers={'sender': component}
    )
        
    return 'Message sent to manager.'

@with_requirements(python_packages=['subprocess'], global_imports=[])
def set_service_cpu(namespace: str, service: str, cpu_cores: float) -> str:
    """
    This function sets the CPU resource allocation (both request and limit) for a specific service in a Kubernetes namespace to a target value using kubectl.
    
    - param namespace: str, the Kubernetes namespace where the service is deployed
    - param service: str, the name of the service to adjust resources for
    - param cpu_cores: float, the target CPU cores to set (absolute value)
    
    - return: str, the result of the operation
    
    Note: 
    - ALWAYS call print() to report the result so that planner can get the result.
    - This function updates both CPU request and limit with the same value.
    - CPU resources in Kubernetes are measured in cores, where 1.0 represents one full CPU core.
    - The minimum allowed value is 50m (0.05) cores and maximum is 800m (0.8) cores.
    
    Example:
    >>> from src.agent.tool_functions_for_maintainer import set_service_cpu
    >>> namespace = 'default'
    >>> service = 'catalogue'
    >>> cpu_cores = 0.5
    >>> result = set_service_cpu(namespace=namespace, service=service, cpu_cores=cpu_cores)
    >>> print(result) # output the result so that planner can get it.
    CPU resources for service 'catalogue' in namespace 'default' set to 0.5 cores.
    """
    import subprocess
    import json
    
    # Minimum and maximum CPU allocation
    MIN_CPU_CORES = 0.05  # 50m
    MAX_CPU_CORES = 0.8   # 800m
    
    # Validate CPU allocation
    if cpu_cores < MIN_CPU_CORES:
        return f"Error: CPU allocation of {cpu_cores} cores is below minimum allowed value of {MIN_CPU_CORES} cores (50m)"
    
    if cpu_cores > MAX_CPU_CORES:
        return f"Error: CPU allocation of {cpu_cores} cores is above maximum allowed value of {MAX_CPU_CORES} cores (800m)"
    
    new_cpu_str = str(cpu_cores)
    
    # Find the deployment associated with the service
    try:
        cmd = f"kubectl get deployments -n {namespace} -o json"
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        deployments = json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        return f"Error executing kubectl command: {e.stderr}"
    
    # Find the deployment for the specified service
    target_deployment = None
    for deployment in deployments['items']:
        if service in deployment['metadata']['name']:
            target_deployment = deployment['metadata']['name']
            break
    
    if not target_deployment:
        return f"Error: No deployment found for service '{service}' in namespace '{namespace}'"
    
    # Get the container name
    try:
        cmd = f"kubectl get deployment {target_deployment} -n {namespace} -o jsonpath='{{.spec.template.spec.containers[0].name}}'"
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        container_name = result.stdout.strip().strip("'")
    except subprocess.CalledProcessError as e:
        return f"Error getting container name: {e.stderr}"
    
    # Apply the changes using kubectl patch
    try:
        patch_json = json.dumps({
            "spec": {
                "template": {
                    "spec": {
                        "containers": [
                            {
                                "name": container_name,
                                "resources": {
                                    "limits": {"cpu": new_cpu_str},
                                    "requests": {"cpu": new_cpu_str}
                                }
                            }
                        ]
                    }
                }
            }
        })
        
        cmd = f"kubectl patch deployment {target_deployment} -n {namespace} --type='strategic' --patch='{patch_json}'"
        subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        return f"Error updating CPU allocation: {e.stderr}"
    
    return f"CPU resources for service '{service}' in namespace '{namespace}' set to {cpu_cores} cores."

# use this list to store all the functions, do not change the name
functions = [report_result, query_prometheus, set_service_cpu]