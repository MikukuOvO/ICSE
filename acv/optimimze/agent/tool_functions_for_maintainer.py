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
    This function sets the CPU resource allocation for a specific service's pods 
    in a Kubernetes namespace using kubectl patch with the resize subresource.
    
    - param namespace: str, the Kubernetes namespace where the service is deployed
    - param service: str, the name of the service to adjust resources for
    - param cpu_cores: float, the target CPU cores to set (absolute value)
    
    - return: str, the result of the operation
    
    Note: 
    - This function updates both CPU request and limit with the same value.
    - CPU resources in Kubernetes are measured in cores, where 1.0 represents one full CPU core.
    - The minimum allowed value is 50m (0.05) cores and maximum is 2.0 cores.
    - The function checks if the change is significant (> 1/4 of current allocation) before applying.
    - Requires Kubernetes v1.33+ with InPlacePodVerticalScaling feature enabled.
    """
    import subprocess
    import json
    import re
    
    # Minimum and maximum CPU allocation
    MIN_CPU_CORES = 0.05  # 50m
    MAX_CPU_CORES = 2.0   # 2000m
    
    # Validate CPU allocation
    if cpu_cores < MIN_CPU_CORES:
        return f"Error: CPU allocation of {cpu_cores} cores is below minimum allowed value of {MIN_CPU_CORES} cores (50m)"
    
    if cpu_cores > MAX_CPU_CORES:
        return f"Error: CPU allocation of {cpu_cores} cores is above maximum allowed value of {MAX_CPU_CORES} cores (2000m)"
    
    new_cpu_str = str(cpu_cores)
    
    # Find the pods associated with the service
    try:
        cmd = f"kubectl get pods -n {namespace} -l app={service} -o json"
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        pods_json = json.loads(result.stdout)
        
        if not pods_json['items']:
            # Try alternative selector patterns if no pods found
            cmd = f"kubectl get pods -n {namespace} -o json"
            result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
            all_pods_json = json.loads(result.stdout)
            
            # Filter pods that contain the service name
            pods_json['items'] = [pod for pod in all_pods_json['items'] 
                                if service in pod['metadata']['name']]
        
        if not pods_json['items']:
            return f"Error: No pods found for service '{service}' in namespace '{namespace}'"
        
    except subprocess.CalledProcessError as e:
        return f"Error executing kubectl command: {e.stderr}"
    
    results = []
    
    # Process each pod
    for pod in pods_json['items']:
        pod_name = pod['metadata']['name']
        container_name = pod['spec']['containers'][0]['name']
        
        # Get current CPU allocation
        try:
            # Get current CPU allocation from the pod spec
            current_cpu = None
            if 'resources' in pod['spec']['containers'][0]:
                resources = pod['spec']['containers'][0]['resources']
                if 'limits' in resources and 'cpu' in resources['limits']:
                    cpu_limit = resources['limits']['cpu']
                    
                    # Handle millicore format (e.g., "500m")
                    if 'm' in cpu_limit:
                        current_cpu = float(cpu_limit.replace('m', '')) / 1000
                    else:
                        current_cpu = float(cpu_limit)
            
            if current_cpu is None:
                results.append(f"Warning: Could not determine current CPU allocation for pod '{pod_name}', proceeding with update")
            else:
                # Calculate delta and check if change is significant
                delta = abs(cpu_cores - current_cpu)
                if delta > (current_cpu / 4):
                    results.append(f"Error: For pod '{pod_name}', the change in CPU allocation ({delta:.3f} cores) is too large (must be <= {current_cpu/4:.3f} cores, which is 1/4 of the current allocation of {current_cpu:.3f} cores)")
                    continue
        
        except Exception as e:
            results.append(f"Error getting current CPU allocation for pod '{pod_name}': {str(e)}")
            continue
        
        # Apply the changes using kubectl patch with the resize subresource
        try:
            patch = json.dumps({
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
            })
            
            # Use the exact command structure from the reference
            cmd = [
                "kubectl", "patch", "pod", pod_name,
                "-n", namespace,
                "--subresource", "resize",
                "--type", "strategic",
                "-p", patch
            ]
            
            resize_result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            if current_cpu:
                results.append(f"CPU resources for pod '{pod_name}' in namespace '{namespace}' changed from {current_cpu} to {cpu_cores} cores.")
            else:
                results.append(f"CPU resources for pod '{pod_name}' in namespace '{namespace}' set to {cpu_cores} cores.")
                
        except subprocess.CalledProcessError as e:
            results.append(f"Error updating CPU allocation for pod '{pod_name}': {e.stderr}")
    
    if not results:
        return f"No pods were processed for service '{service}' in namespace '{namespace}'"
    
    return "\n".join(results)

# use this list to store all the functions, do not change the name
functions = [report_result, query_prometheus, set_service_cpu]