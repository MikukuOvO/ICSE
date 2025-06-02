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
    >>> from detect.agent.tool_functions_for_maintainer import query_prometheus
    >>> promQL = '<metric_name>{<label_selector>}'
    >>> result = query_prometheus(promQL=promQL, duration='?min', step='?s')
    >>> print(result) # output the result so that planner can get it.
    [['2024-06-20 02:17:20', 0.0], ['2024-06-20 02:18:20', 0.0], ['2024-06-20 02:19:20', 0.0]], ...
    """
    from ..module.prometheus_client import PrometheusClient
    prometheus_client = PrometheusClient()
    result: list[list[str, int]] = prometheus_client.query_range(promQL, **kwargs)
    return result

def query_prometheus_list(promQL_list: list, **kwargs) -> dict:
    """
    This function is used to query prometheus with a list of promQL queries at once.
    - param promQL_list: list, a list of promQL queries to be executed
    - param kwargs: dict, parameters to be passed to the query, must contain one of the following: (start_time, end_time), duration
    - return: dict, a dictionary mapping each promQL to its query result

    Note: 
    - ALWAYS call print() to report the result so that planner can get the result.
    - ALWAYS call query_prometheus_list with full parameters, including promQL_list, duration and step.

    Example: 
    >>> from detect.agent.tool_functions_for_maintainer import query_prometheus_list
    >>> promQL_list = ['<metric1>{<label_selector>}', '<metric2>{<label_selector>}']
    >>> result = query_prometheus_list(promQL_list=promQL_list, duration='10m', step='30s')
    >>> print(result) # output the result so that planner can get it.
    {'<metric1>{<label_selector>}': [['2024-06-20 02:17:20', 0.0], ['2024-06-20 02:18:20', 0.0]], '<metric2>{<label_selector>}': [['2024-06-20 02:17:20', 1.0], ['2024-06-20 02:18:20', 1.5]]}
    """
    from ..module.prometheus_client import PrometheusClient
    prometheus_client = PrometheusClient()
    
    results = {}
    for promQL in promQL_list:
        result: list[list[str, int]] = prometheus_client.query_range(promQL, **kwargs)
        results[promQL] = result
    
    return results

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
    >>> from detect.agent.tool_functions_for_maintainer import report_result
    >>> component = 'catalogue'
    >>> message = 'The task is completed.'
    >>> message_type = 'RESPONSE'
    >>> result = report_result(component=component, message=messages, message_type=message_type)
    >>> print(result) # output the result so that planner can get it.
    Message sent to manager.
    """
    from ..module import RabbitMQ, load_config

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

functions = [report_result, query_prometheus, query_prometheus_list]