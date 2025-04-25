#!/usr/bin/env python3
import time
import datetime
import yaml
import sys
import os
from ..agent.tool_functions_for_maintainer import query_prometheus, report_result
from typing import Literal

def report_result(component: str, message: str, message_type: Literal['ISSUE', 'RESPONSE']) -> str:
    from .message_queue import RabbitMQ
    from .utils import load_config

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

def get_metrics_map():
    """
    Load metrics configuration from YAML file.
    """
    # Use a default YAML file. Optionally, allow override via sys.argv[4].
    metrics_file = 'metrics_collection.yaml'
    if len(sys.argv) > 4:
        metrics_file = sys.argv[4]
    
    yaml_path = os.path.join('src', 'conf', metrics_file)
    with open(yaml_path, encoding="utf-8") as input_file:
        data = yaml.safe_load(input_file)
    # The YAML file is expected to have a top-level key 'train-ticket'
    return data.get('train-ticket', {})

def monitor_service_metrics():
    """
    Continuously monitors service metrics from Prometheus based on metrics defined in YAML.
    Filters for metrics with deploymentName "home-timeline-service".
    Reports issues and responses to the manager using report_result.
    """
    # Load metrics configuration
    metrics_map = get_metrics_map()
    
    # Filter metrics for home-timeline-service
    home_timeline_metrics = {}
    for metric_name, metric_info in metrics_map.items():
        if metric_info.get('deploymentName') == "ts-route-service":
            home_timeline_metrics[metric_name] = metric_info
    
    if not home_timeline_metrics:
        message = "No metrics found for ts-route-service in the configuration."
        print(message)
        report_result(
            component="metrics-monitor", 
            message=message, 
            message_type="ISSUE"
        )
        return
    
    # Report starting monitoring
    start_message = f"Starting continuous monitoring of ts-route-service metrics. Found {len(home_timeline_metrics)} metrics to monitor."
    print(start_message)
    report_result(
        component="metrics-monitor",
        message=start_message,
        message_type="RESPONSE"
    )
    
    # Log metrics being monitored
    metrics_details = []
    for name, info in home_timeline_metrics.items():
        metrics_details.append(f"Metric: {name}, PromQL: {info.get('promql', 'No PromQL defined')}")
    
    report_result(
        component="metrics-monitor",
        message=f"Monitoring the following metrics:\n" + "\n".join(metrics_details),
        message_type="RESPONSE"
    )
    
    try:
        while True:
            # Current timestamp for logging
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n[{current_time}] Querying metrics...")
            
            # Query each metric for home-timeline-service
            responses = []
            
            for metric_name, metric_info in home_timeline_metrics.items():
                promql = metric_info.get('promql')
                if not promql:
                    message = f"No PromQL defined for {metric_name}, skipping..."
                    print(message)
                    continue
                
                try:
                    # Query Prometheus with a shorter timeframe for more recent data
                    result = query_prometheus(
                        promQL=promql, 
                        duration="2m",  # Look at the last 2 minutes of data
                        step="10s"      # Get data points every 10 seconds
                    )
                    
                    # Print and collect the results
                    metric_response = f"Metric: {metric_name} - Retrieved {len(result)} data points"
                    data_points = []
                    
                    # Display the data points
                    if result:
                        for timestamp, value in result:
                            # Format the value to 2 decimal places if it's a float
                            if isinstance(value, float):
                                formatted_value = f"{value:.2f}"
                            else:
                                formatted_value = value
                            
                            data_point = f"  {timestamp}: {formatted_value}"
                            print(data_point)
                            data_points.append(data_point)
                        
                        # Extract the latest value for additional analysis
                        latest_timestamp, latest_value = result[-1]
                        
                        # Include the latest value in the response without alerts
                        latest_value_msg = f"  Latest value for {metric_name}: {latest_value:.2f if isinstance(latest_value, float) else latest_value}"
                        print(latest_value_msg)
                        data_points.append(latest_value_msg)
                        
                        # Add data points to the response
                        metric_response += "\n" + "\n".join(data_points)
                    else:
                        no_data_msg = f"  No data returned from query for {metric_name}"
                        print(no_data_msg)
                        metric_response += "\n" + no_data_msg
                    
                    responses.append(metric_response)
                
                except Exception as e:
                    error_msg = f"Error querying {metric_name}: {str(e)}"
                    print(error_msg)
                    # Just log the error without reporting it as an issue
            
            # Report responses with metric data
            report_result(
                component="metrics-monitor",
                message=f"Metrics update at {current_time}:\n" + "\n".join(responses),
                message_type="RESPONSE"
            )
            
            # Wait before the next fetch (10 seconds)
            print(f"\nWaiting 10 seconds before next query...")
            time.sleep(10)
            
    except KeyboardInterrupt:
        shutdown_msg = "Monitoring stopped by user."
        print(f"\n{shutdown_msg}")
        report_result(
            component="metrics-monitor",
            message=shutdown_msg,
            message_type="RESPONSE"
        )
    except Exception as e:
        error_msg = f"Error during monitoring: {str(e)}"
        print(f"\n{error_msg}")
        report_result(
            component="metrics-monitor",
            message=error_msg,
            message_type="ISSUE"
        )