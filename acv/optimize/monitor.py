import subprocess
import csv
import os
import time
import json
import re
import yaml
from datetime import datetime
 
def query_prometheus(promQL: str, **kwargs) -> list:
    from acv.optimize.module.prometheus_client import PrometheusClient
    prometheus_client = PrometheusClient()
    result = prometheus_client.query(promQL, **kwargs)
    return result
 
def load_metrics_config(config_file="acv/conf/metrics_collection.yaml"):
    """
    Load metrics configuration from YAML file.
   
    Args:
        config_file (str): Path to the metrics configuration file
       
    Returns:
        dict: Loaded metrics configuration
    """
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        print(f"Error loading metrics configuration: {e}")
        return {}
 
def query_metrics_for_deployments(config, namespace):
    """
    Query Prometheus for metrics defined in the configuration.
    This now handles both latency and workload metrics.
   
    Args:
        config (dict): Metrics configuration
        namespace (str): Kubernetes namespace
       
    Returns:
        dict: Dictionary of metric results by deployment and metric type
    """
    results = {}
    # Keywords for identifying different metric types
    latency_keywords = ["latency", "duration", "response_time"]
    workload_keywords = ["workload", "requests_total", "throughput", "rate"]
    resource_keywords = ["cpu_usage", "memory_usage", "cpu", "memory"]
 
    for app_name, app_metrics in config.items():
        print(f"Querying metrics for application: {app_name}")
       
        for metric_name, metric_config in app_metrics.items():
            # Skip commented metrics
            if metric_name.startswith("#"):
                continue
               
            deployment_name = metric_config.get("deploymentName")
            promql = metric_config.get("promql")
           
            if not deployment_name or not promql:
                print(f"Missing deploymentName or promQL for {metric_name}, skipping")
                continue
               
            try:
                print(f"Querying Prometheus for {metric_name} in deployment {deployment_name}")
                result = query_prometheus(promql)
 
                if deployment_name not in results:
                    results[deployment_name] = {}
 
                if isinstance(result, (int, float)):
                    results[deployment_name][metric_name] = result
                elif isinstance(result, list) and len(result) > 0:
                    if isinstance(result[0], list) and len(result[0]) > 1:
                        results[deployment_name][metric_name] = result[0][1]
                    else:
                        results[deployment_name][metric_name] = result[0]
                else:
                    results[deployment_name][metric_name] = "N/A"
            except Exception as e:
                print(f"Error querying Prometheus for {metric_name}: {e}")
                if deployment_name not in results:
                    results[deployment_name] = {}
                results[deployment_name][metric_name] = "ERROR"
   
    return results
 
def get_running_pods_for_deployments(namespace, deployment_names):
    """
    Get one running pod for each deployment
   
    Args:
        namespace (str): Kubernetes namespace
        deployment_names (list): List of deployment names
       
    Returns:
        dict: Dictionary mapping deployment names to their running pod names
    """
    deployment_to_pod = {}
   
    for deployment in deployment_names:
        try:
            # Get pods for this deployment
            result = subprocess.run(
                ["kubectl", "get", "pods", "-n", namespace, "-l", f"app={deployment}", "--field-selector", "status.phase=Running", "-o", "json"],
                check=True,
                capture_output=True,
                text=True
            )
            pods = json.loads(result.stdout)["items"]
           
            # If there's at least one running pod, use the first one
            if pods:
                deployment_to_pod[deployment] = pods[0]["metadata"]["name"]
            else:
                print(f"No running pods found for deployment {deployment}")
                deployment_to_pod[deployment] = None
        except subprocess.CalledProcessError as e:
            print(f"Error getting pods for deployment {deployment}: {e}")
            deployment_to_pod[deployment] = None
        except json.JSONDecodeError as e:
            print(f"Error parsing pod JSON for deployment {deployment}: {e}")
            deployment_to_pod[deployment] = None
   
    return deployment_to_pod
 
def monitor_k8s_resources(namespace, output_file, metrics_config_file="acv/conf/metrics_collection.yaml",
                         interval_seconds=60, duration_minutes=None):
    """
    Monitor Kubernetes CPU, memory requests, CPU usage, memory usage, and both latency and workload metrics
    for all deployments in a namespace.
   
    Args:
        namespace (str): Kubernetes namespace to monitor
        output_file (str): Path to the CSV output file
        metrics_config_file (str): Path to the metrics configuration file
        interval_seconds (int): Polling interval in seconds
        duration_minutes (int, optional): Total monitoring duration in minutes. If None, runs indefinitely.
    """
    # Calculate end time if duration is specified
    end_time = None
    if duration_minutes:
        end_time = time.time() + (duration_minutes * 60)
   
    # Load metrics configuration
    metrics_config = load_metrics_config(metrics_config_file)
   
    # Get all deployments in the namespace
    try:
        result = subprocess.run(
            ["kubectl", "get", "deployments", "-n", namespace, "-o", "json"],
            check=True,
            capture_output=True,
            text=True
        )
        deployments = json.loads(result.stdout)["items"]
        deployment_names = [dep["metadata"]["name"] for dep in deployments]
    except subprocess.CalledProcessError as e:
        print(f"Error getting deployments: {e}")
        return
    except json.JSONDecodeError as e:
        print(f"Error parsing deployment JSON: {e}")
        return
 
    # Create CSV file with headers
    file_exists = os.path.isfile(output_file)
   
    # Basic resource headers
    headers = ["timestamp"]
    for name in deployment_names:
        headers.extend([f"cpu_requests_{name}", f"mem_requests_{name}", f"cpu_usage_{name}", f"mem_usage_{name}"])
   
    # Add headers for all metrics (both latency and workload)
    for app_name, app_metrics in metrics_config.items():
        for metric_name, metric_config in app_metrics.items():
            if metric_name.startswith("#"):
                continue
               
            # Get deployment name for this metric
            deployment_name = metric_config.get("deploymentName")
            if deployment_name:
                # Format the header to be consistent with cpu_usage and mem_usage format
                header = f"{metric_name}_{deployment_name}"
                headers.append(header)
            else:
                headers.append(metric_name)
   
    # If the file doesn't exist, create it with headers
    if not file_exists:
        with open(output_file, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(headers)
   
    print(f"Monitoring {len(deployment_names)} deployments in namespace '{namespace}'")
    print(f"Data will be saved to {output_file}")
    print(f"Polling every {interval_seconds} seconds")
    if duration_minutes:
        print(f"Monitoring will run for {duration_minutes} minutes")
    else:
        print("Monitoring will run until interrupted (Ctrl+C)")
   
    try:
        while True:
            # Check if we've reached the end time
            if end_time and time.time() >= end_time:
                print(f"Reached specified duration of {duration_minutes} minutes. Exiting.")
                break
           
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            row_data = [timestamp]
           
            # Get one running pod for each deployment
            deployment_to_pod = get_running_pods_for_deployments(namespace, deployment_names)
           
            # Get resource requests for each deployment
            for name in deployment_names:
                pod_name = deployment_to_pod.get(name)
               
                if not pod_name:
                    row_data.extend(["N/A", "N/A", "N/A", "N/A"])
                    continue
               
                try:
                    # Use kubectl describe pod to get the pod details
                    result = subprocess.run(
                        ["kubectl", "get", "pod", pod_name, "-n", namespace, "-o", "json"],
                        check=True,
                        capture_output=True,
                        text=True
                    )
                   
                    pod_data = json.loads(result.stdout)
 
                    SIDECAR_KEYWORDS = ['sidecar', 'istio', 'linkerd']
 
                    cpu_requests = "N/A"
                    mem_requests = "N/A"
 
                    # 遍历容器信息
                    for container in pod_data["spec"]["containers"]:
                        container_name = container["name"]
                        is_sidecar = any(keyword in container_name.lower() for keyword in SIDECAR_KEYWORDS)
 
                        if not is_sidecar:
                            requests = container.get("resources", {}).get("requests", {})
                            cpu_requests = requests.get("cpu", "not set")
                            mem_requests = requests.get("memory", "not set")
 
                    if cpu_requests[-1] != "m":
                        cpu_requests = f"{int(float(cpu_requests)*1000)}m"
                   
                    # Query Prometheus for CPU and memory usage
                    try:
                        # Query for CPU usage (in cores, convert to millicores by multiplying by 1000)
                        cpu_usage_query = f'sum(rate(container_cpu_usage_seconds_total{{namespace="{namespace}",pod=~"{name}-[a-zA-Z0-9]+-[a-zA-Z0-9]+"}}[5m]))'
                        cpu_usage_result = query_prometheus(cpu_usage_query)
                       
                        if isinstance(cpu_usage_result, list) and len(cpu_usage_result) > 0 and isinstance(cpu_usage_result[0], list) and len(cpu_usage_result[0]) > 1:
                            # Convert from cores to millicores (m) by multiplying by 1000
                            cpu_cores = float(cpu_usage_result[0][1])
                            cpu_millicores = cpu_cores * 1000
                            cpu_usage = f"{cpu_millicores:.0f}m"
                        else:
                            cpu_usage = "N/A"
                       
                        # Query for memory usage (in bytes, convert to Mi)
                        mem_usage_query = f'sum(container_memory_working_set_bytes{{namespace="{namespace}",pod=~"{name}-[a-zA-Z0-9]+-[a-zA-Z0-9]+"}})'
                        mem_usage_result = query_prometheus(mem_usage_query)
                       
                        if isinstance(mem_usage_result, list) and len(mem_usage_result) > 0 and isinstance(mem_usage_result[0], list) and len(mem_usage_result[0]) > 1:
                            # Convert from bytes to MiB
                            mem_bytes = float(mem_usage_result[0][1])
                            mem_mi = mem_bytes / (1024 * 1024)  # Convert bytes to MiB
                            mem_usage = f"{mem_mi:.0f}Mi"
                        else:
                            mem_usage = "N/A"
                       
                        row_data.extend([cpu_requests, mem_requests, cpu_usage, mem_usage])
                    except Exception as e:
                        print(f"Error querying Prometheus for resource usage of {name}: {e}")
                        row_data.extend([cpu_requests, mem_requests, "ERROR", "ERROR"])
               
                except subprocess.CalledProcessError as e:
                    print(f"Error getting data for pod {pod_name}: {e}")
                    row_data.extend(["ERROR", "ERROR", "ERROR", "ERROR"])
           
            # Query Prometheus for all metrics (both latency and workload)
            prometheus_metrics = query_metrics_for_deployments(metrics_config, namespace)
           
            # Add all metrics to the row data
            metric_values = {}
            for app_name, app_metrics in metrics_config.items():
                for metric_name, metric_config in app_metrics.items():
                    if metric_name.startswith("#"):
                        continue
 
                    deployment_name = metric_config.get("deploymentName")
                    if deployment_name:
                        # Format the metric name to be consistent with cpu_usage and mem_usage format
                        header_name = f"{metric_name}_{deployment_name}"
                       
                        if deployment_name in prometheus_metrics and metric_name in prometheus_metrics[deployment_name]:
                            metric_value = prometheus_metrics[deployment_name][metric_name]
                            metric_values[header_name] = str(metric_value)
                        else:
                            metric_values[header_name] = "N/A"
                    else:
                        if deployment_name in prometheus_metrics and metric_name in prometheus_metrics[deployment_name]:
                            metric_value = prometheus_metrics[deployment_name][metric_name]
                            metric_values[metric_name] = str(metric_value)
                        else:
                            metric_values[metric_name] = "N/A"
           
            # Add metrics in the same order as headers
            for header in headers[1:]:  # Skip timestamp which is already added
                if header.startswith("cpu_requests_") or header.startswith("mem_requests_") or \
                   header.startswith("cpu_usage_") or header.startswith("mem_usage_"):
                    continue  # These are already added
               
                if header in metric_values:
                    row_data.append(metric_values[header])
                else:
                    row_data.append("N/A")
           
            # Append row to CSV
            with open(output_file, 'a', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(row_data)
           
            print(f"Recorded metrics at {timestamp}")
           
            # Sleep until next interval
            time.sleep(interval_seconds)
   
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        print(f"Monitoring complete. Data saved to {output_file}")
 
if __name__ == "__main__":
    import argparse
   
    parser = argparse.ArgumentParser(description="Monitor Kubernetes resource requests, latency and workload metrics")
    parser.add_argument("--namespace", "-n", required=True, help="Kubernetes namespace to monitor")
    parser.add_argument("--output", "-o", default="k8s_resource_metrics.csv", help="Output CSV file path")
    parser.add_argument("--metrics-config", "-m", default="acv/conf/metrics_collection.yaml", help="Metrics configuration file path")
    parser.add_argument("--interval", "-i", type=int, default=60, help="Polling interval in seconds")
    parser.add_argument("--duration", "-d", type=int, help="Total monitoring duration in minutes")
   
    args = parser.parse_args()
   
    # Normal foreground execution
    monitor_k8s_resources(
        namespace=args.namespace,
        output_file=args.output,
        metrics_config_file=args.metrics_config,
        interval_seconds=args.interval,
        duration_minutes=args.duration
    )