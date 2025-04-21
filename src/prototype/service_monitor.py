import yaml
import json
import subprocess
import datetime
import time
import os

def convert_memory_to_mib(memory_value):
    """
    Convert various memory formats to MiB
    """
    if isinstance(memory_value, (int, float)):
        return memory_value
    
    # Handle string formats
    if memory_value.endswith('Mi'):
        return float(memory_value[:-2])
    elif memory_value.endswith('Gi'):
        return float(memory_value[:-2]) * 1024
    elif memory_value.endswith('Ki'):
        return float(memory_value[:-2]) / 1024
    elif memory_value.endswith('k'):
        return float(memory_value[:-1]) / 1024
    elif memory_value.endswith('M'):
        return float(memory_value[:-1])
    elif memory_value.endswith('G'):
        return float(memory_value[:-1]) * 1024
    elif memory_value.endswith('T'):
        return float(memory_value[:-1]) * 1024 * 1024
    else:
        # Assume bytes if no unit
        return float(memory_value) / (1024*1024)

def convert_cpu_to_millicores(cpu_value):
    """
    Convert CPU value to millicores
    """
    if isinstance(cpu_value, (int, float)):
        return cpu_value
    
    if cpu_value.endswith('m'):
        return float(cpu_value[:-1])
    else:
        return float(cpu_value) * 1000

def setup_vpa():
    """
    Set up VPA for the ts-route-service
    Returns the deployment name and namespace
    """
    deployment_name = "ts-route-service"
    namespace = "train-ticket"
    
    # Create a VPA YAML configuration
    vpa_yaml = f"""apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: {deployment_name}-vpa
  namespace: {namespace}
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {deployment_name}
  updatePolicy:
    updateMode: "Auto"
    minReplicas: 1  # Allow single replica updates
  resourcePolicy:
    containerPolicies:
    - containerName: '*'
      minAllowed:
        cpu: 100m
        memory: 300Mi
      maxAllowed:
        cpu: 1000m
        memory: 4000Mi
"""
    
    # Write the VPA configuration to a file
    file_path = os.path.join(os.getcwd(), "vpa.yaml")
    try:
        with open(file_path, "w") as f:
            f.write(vpa_yaml)
    except Exception as e:
        print(f"Error writing VPA configuration to file: {e}")
        raise
    
    # Apply the VPA configuration
    apply_cmd = f"kubectl apply -f vpa.yaml -n train-ticket"
    result = subprocess.run(
        apply_cmd,
        shell=True,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    if result.returncode == 0:
        print(f"Successfully configured Kubernetes VPA for {deployment_name} in {namespace} namespace")
    else:
        print(f"Failed to configure Kubernetes VPA: {result.stderr}")
        raise Exception("Failed to configure VPA")
        
    return deployment_name, namespace

def cleanup_vpa(deployment_name, namespace):
    """
    Clean up the VPA configuration
    """
    print("Removing VPA configuration...")
    try:
        subprocess.run(f"kubectl delete vpa {deployment_name}-vpa -n {namespace}", shell=True)
        print(f"Deleted VPA for {deployment_name}")
    except:
        print("Failed to delete VPA")

def get_services_from_yaml():
    """
    Read service information from the YAML file
    """
    yaml_path = "src/conf/service_maintainers_optimize.yaml"
    try:
        with open(yaml_path, 'r') as f:
            services_config = yaml.safe_load(f)
        
        # Extract service names from the deployments section
        services = []
        if 'deployments' in services_config:
            services = [service for service in services_config['deployments']]
        
        if not services:
            print("No services found in the YAML file. Using default service.")
            services = ["ts-route-service"]
            
        return services
    except Exception as e:
        print(f"Error reading YAML file: {e}")
        return ["ts-route-service"]  # Default to home-timeline-service if there's an error

def get_pod_resources(pod_name, namespace):
    """
    Get resource information for a specific pod
    """
    pod_info = {
        'name': pod_name,
        'cpu_request': None,
        'cpu_limit': None,
        'cpu_usage': None,
        'memory_request': None,
        'memory_limit': None,
        'memory_usage': None
    }
    
    # Get pod spec to extract requests and limits
    try:
        cmd = f"kubectl get pod {pod_name} -n {namespace} -o json"
        result = subprocess.run(
            cmd,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if result.returncode == 0:
            pod_data = json.loads(result.stdout)
            
            # Get resources from pod spec
            if "spec" in pod_data and "containers" in pod_data["spec"]:
                containers = pod_data["spec"]["containers"]
                for container in containers:
                    if "resources" in container:
                        resources = container["resources"]
                        
                        # Get CPU request
                        if "requests" in resources and "cpu" in resources["requests"]:
                            try:
                                cpu_request = resources["requests"]["cpu"]
                                request_value = convert_cpu_to_millicores(cpu_request)
                                pod_info['cpu_request'] = request_value
                                print(f"  CPU request: {request_value}m")
                            except (ValueError, TypeError) as e:
                                print(f"  Error converting CPU request '{cpu_request}': {e}")
                        
                        # Get CPU limit
                        if "limits" in resources and "cpu" in resources["limits"]:
                            try:
                                cpu_limit = resources["limits"]["cpu"]
                                limit_value = convert_cpu_to_millicores(cpu_limit)
                                pod_info['cpu_limit'] = limit_value
                                print(f"  CPU limit: {limit_value}m")
                            except (ValueError, TypeError) as e:
                                print(f"  Error converting CPU limit '{cpu_limit}': {e}")
                            
                        # Get Memory request
                        if "requests" in resources and "memory" in resources["requests"]:
                            try:
                                memory_request = resources["requests"]["memory"]
                                memory_request_value = convert_memory_to_mib(memory_request)
                                pod_info['memory_request'] = memory_request_value
                                print(f"  Memory request: {memory_request_value}Mi")
                            except (ValueError, TypeError) as e:
                                print(f"  Error converting memory request '{memory_request}': {e}")
                        
                        # Get Memory limit
                        if "limits" in resources and "memory" in resources["limits"]:
                            try:
                                memory_limit = resources["limits"]["memory"]
                                memory_limit_value = convert_memory_to_mib(memory_limit)
                                pod_info['memory_limit'] = memory_limit_value
                                print(f"  Memory limit: {memory_limit_value}Mi")
                            except (ValueError, TypeError) as e:
                                print(f"  Error converting memory limit '{memory_limit}': {e}")
    except Exception as e:
        print(f"  Error getting pod spec: {e}")
    
    # Get actual CPU and Memory usage using metrics-server
    try:
        usage_cmd = f"kubectl top pod {pod_name} -n {namespace} --no-headers"
        usage_result = subprocess.run(
            usage_cmd,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if usage_result.returncode == 0:
            # Parse the output which should be in format: "pod_name cpu_usage memory_usage"
            parts = usage_result.stdout.strip().split()
            if len(parts) >= 3:
                # Extract CPU usage
                try:
                    cpu_usage_str = parts[1]
                    cpu_usage = convert_cpu_to_millicores(cpu_usage_str)
                    pod_info['cpu_usage'] = cpu_usage
                    print(f"  CPU usage: {cpu_usage}m")
                except (ValueError, TypeError) as e:
                    print(f"  Error converting CPU usage '{cpu_usage_str}': {e}")
                
                # Extract Memory usage
                try:
                    memory_usage_str = parts[2]
                    memory_usage = convert_memory_to_mib(memory_usage_str)
                    pod_info['memory_usage'] = memory_usage
                    print(f"  Memory usage: {memory_usage}Mi")
                except (ValueError, TypeError) as e:
                    print(f"  Error converting memory usage '{memory_usage_str}': {e}")
    except Exception as e:
        print(f"  Error getting resource usage: {e}")
    
    return pod_info

def get_vpa_recommendations(deployment_name, namespace):
    """
    Get VPA recommendations for a deployment
    """
    recommendations = {}
    
    # Get CPU recommendation
    try:
        cmd = f"kubectl get vpa {deployment_name}-vpa -n {namespace} -o jsonpath='{{.status.recommendation.containerRecommendations[0].target.cpu}}'"
        result = subprocess.run(
            cmd,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode == 0 and result.stdout:
            vpa_rec = result.stdout
            print(f"VPA recommended CPU for {deployment_name}: {vpa_rec}")
            recommendations['cpu'] = vpa_rec
    except Exception as e:
        print(f"Error getting VPA CPU recommendation: {e}")
    
    # Get Memory recommendation
    try:
        cmd = f"kubectl get vpa {deployment_name}-vpa -n {namespace} -o jsonpath='{{.status.recommendation.containerRecommendations[0].target.memory}}'"
        result = subprocess.run(
            cmd,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode == 0 and result.stdout:
            vpa_mem_rec = result.stdout
            print(f"VPA recommended Memory for {deployment_name}: {vpa_mem_rec}")
            recommendations['memory'] = vpa_mem_rec
    except Exception as e:
        print(f"Error getting VPA Memory recommendation: {e}")
    
    return recommendations

def monitor_services(total_runtime, check_interval):
    """
    Monitor services and collect resource usage data
    Returns timestamps and service_data for further processing
    """
    # Initialize data collection 
    timestamps = []
    service_data = []
    
    # Get services from YAML
    services = get_services_from_yaml()
    print(f"Monitoring the following services: {', '.join(services)}")
    
    # Set up VPA for home-timeline-service
    deployment_name, namespace = setup_vpa()
    
    try:
        elapsed_time = 0
        
        while elapsed_time < total_runtime:
            remaining = total_runtime - elapsed_time
            print(f"\nElapsed time: {elapsed_time} seconds. Remaining: {remaining} seconds.")
            
            # Get current time
            current_time = datetime.datetime.now()
            timestamps.append(current_time)
            
            # Data for this time point
            time_point_data = {
                'time': current_time,
                'services': {}
            }
            
            # For each service, collect pod data
            for service in services:
                service_info = {
                    'name': service,
                    'pods': []
                }
                
                try:
                    # Get all pods for the service
                    cmd = f"kubectl get pods -n {namespace} -l app={service} -o jsonpath='{{.items[*].metadata.name}}'"
                    result = subprocess.run(
                        cmd,
                        shell=True,
                        check=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    
                    if result.returncode == 0 and result.stdout:
                        pod_names = result.stdout.split()
                        
                        if pod_names:
                            print(f"Found {len(pod_names)} pods for service {service}")
                            
                            # Process each pod
                            for pod_name in pod_names:
                                print(f"Checking pod: {pod_name}")
                                
                                # Get pod resources
                                pod_info = get_pod_resources(pod_name, namespace)
                                
                                # Add pod info to this service's data
                                service_info['pods'].append(pod_info)
                        else:
                            print(f"No pods found for service {service}")
                    else:
                        print(f"Failed to get pods for service {service}: {result.stderr}")
                
                except Exception as e:
                    print(f"Error collecting resource data for service {service}: {e}")
                
                # Add service info to this time point's data
                time_point_data['services'][service] = service_info
            
            # Get VPA recommendation only for home-timeline-service
            if deployment_name in services:
                recommendations = get_vpa_recommendations(deployment_name, namespace)
                
                if 'cpu' in recommendations:
                    time_point_data['vpa_recommendation'] = recommendations['cpu']
                if 'memory' in recommendations:
                    time_point_data['vpa_memory_recommendation'] = recommendations['memory']
            
            # Add this time point's data to overall collection
            service_data.append(time_point_data)
            
            # Wait for the shorter of check_interval or remaining time
            wait_time = min(check_interval, remaining)
            if wait_time > 0:
                time.sleep(wait_time)
                elapsed_time += wait_time
            else:
                break
    finally:
        # Clean up the VPA
        cleanup_vpa(deployment_name, namespace)
    
    return timestamps, service_data