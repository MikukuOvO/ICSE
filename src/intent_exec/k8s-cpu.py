#!/usr/bin/env python3
"""
K8s CPU Controller - Script that adjusts both CPU limits and requests
for microservices based on their utilization using --subresource resize.
This approach directly resizes pods without triggering deployments.
"""

import time
import json
import subprocess
from typing import Dict, List, Optional, Tuple

# Configuration
NAMESPACE = "social-network"  # Target namespace
THRESHOLD = 0.05              # CPU utilization threshold (0.05 = 5%)
INTERVAL = 60                 # Sampling interval in seconds
SERVICES = ["compose-post-service", "home-timeline-service", "user-timeline-service"]
REQUEST_RATIO = 1.0           # Requests will be set to this ratio of limits (1.0 = equal)
SCALE_UP_FACTOR = 1.5         # When over threshold, multiply by this factor
SCALE_DOWN_FACTOR = 0.8       # When under threshold, multiply by this factor


def run_command(command: List[str]) -> Tuple[bool, str]:
    """Run a kubectl command and return success/output"""
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode == 0:
            return True, result.stdout
        else:
            print(f"Command failed: {' '.join(command)}")
            print(f"Error: {result.stderr}")
            return False, result.stderr
    except Exception as e:
        print(f"Exception running command: {str(e)}")
        return False, str(e)


def get_pods_for_service(service: str) -> List[str]:
    """Get list of pods for a service"""
    success, output = run_command([
        "kubectl", "get", "pods", 
        "-n", NAMESPACE, 
        "-l", f"app={service}", 
        "-o", "jsonpath={.items[*].metadata.name}"
    ])
    
    if not success or not output.strip():
        print(f"No pods found for service {service}")
        # Try alternative labels if the standard app label doesn't work
        success, output = run_command([
            "kubectl", "get", "pods", 
            "-n", NAMESPACE, 
            "--selector", f"name={service}", 
            "-o", "jsonpath={.items[*].metadata.name}"
        ])
        
        if not success or not output.strip():
            # Try to list all pods and grep for the service name
            success, output = run_command([
                "kubectl", "get", "pods", 
                "-n", NAMESPACE, 
                "-o", "name"
            ])
            
            if success and output.strip():
                pods = [p.split('/')[-1] for p in output.strip().split() if service in p]
                if pods:
                    print(f"Found {len(pods)} pod(s) for service {service} by name: {', '.join(pods)}")
                    return pods
            
            return []
    
    pods = output.strip().split()
    print(f"Found {len(pods)} pod(s) for service {service}: {', '.join(pods)}")
    return pods


def get_cpu_usage(pod: str) -> Optional[float]:
    """Get current CPU usage for a pod in millicores"""
    success, output = run_command(["kubectl", "top", "pod", pod, "-n", NAMESPACE])
    
    if not success:
        print(f"Failed to get CPU metrics for pod {pod}")
        return None
    
    try:
        # Parse the output (skip header line)
        lines = output.strip().split('\n')
        if len(lines) < 2:
            # Sometimes the output doesn't have a header
            pod_line = lines[0]
        else:
            pod_line = lines[1]
            
        # Extract CPU usage (format: "POD_NAME CPU(m) MEMORY")
        parts = pod_line.split()
        cpu_usage_str = parts[1] if len(parts) > 1 else ""
        
        # Convert from "123m" format to numeric value
        if cpu_usage_str.endswith('m'):
            cpu_usage = float(cpu_usage_str[:-1])
        else:
            # Handle case where it might be in cores instead of millicores
            cpu_usage = float(cpu_usage_str) * 1000
            
        return cpu_usage
    except (IndexError, ValueError) as e:
        print(f"Error parsing CPU usage for pod {pod}: {str(e)}")
        print(f"Raw output: {output}")
        return None


def get_container_for_pod(pod: str) -> Optional[str]:
    """Find the appropriate container name in the pod"""
    success, output = run_command([
        "kubectl", "get", "pod", pod, 
        "-n", NAMESPACE, 
        "-o", "json"
    ])
    
    if not success:
        return None
    
    try:
        pod_data = json.loads(output)
        
        # Get container names
        containers = pod_data.get('spec', {}).get('containers', [])
        if not containers:
            print(f"No containers found in pod {pod}")
            return None
            
        # Try to find the correct container name
        container_name = None
        
        # First pass: exact match with service name
        for container in containers:
            name = container.get('name', '')
            if name in SERVICES:
                container_name = name
                break
                
        # Second pass: partial match with service name
        if not container_name:
            for service in SERVICES:
                for container in containers:
                    name = container.get('name', '')
                    if service in name:
                        container_name = name
                        break
                if container_name:
                    break
                    
        # Fall back to first container
        if not container_name and containers:
            container_name = containers[0].get('name')
            
        return container_name
        
    except json.JSONDecodeError:
        print(f"Error parsing pod data for {pod}")
        return None


def get_current_pod_resources(pod: str, container: str) -> Tuple[Optional[str], Optional[str]]:
    """Get current CPU requests and limits for a container in a pod"""
    success, output = run_command([
        "kubectl", "get", "pod", pod,
        "-n", NAMESPACE,
        "-o", "jsonpath={.spec.containers[?(@.name==\"" + container + "\")].resources}"
    ])
    
    if not success:
        return None, None
    
    try:
        resources = json.loads(output)
        limits = resources.get('limits', {}).get('cpu')
        requests = resources.get('requests', {}).get('cpu')
        return requests, limits
    except json.JSONDecodeError:
        return None, None


def parse_cpu_value(cpu_value: str) -> int:
    """Parse CPU value like '200m' or '0.5' to millicores (int)"""
    if not cpu_value:
        return 0
        
    if cpu_value.endswith('m'):
        return int(cpu_value[:-1])
    else:
        # Convert from cores to millicores
        return int(float(cpu_value) * 1000)


def resize_pod_cpu_resources(pod: str, container: str, cpu_limit_m: int) -> bool:
    """Update CPU limits and requests for a container in a pod using --subresource resize"""
    # Set requests equal to limits for better predictability (or use REQUEST_RATIO)
    cpu_request_m = int(cpu_limit_m * REQUEST_RATIO)
    
    # Get current values for comparison
    current_request_str, current_limit_str = get_current_pod_resources(pod, container)
    current_request_m = parse_cpu_value(current_request_str) if current_request_str else 0
    current_limit_m = parse_cpu_value(current_limit_str) if current_limit_str else 0
    
    print(f"  Current resources: requests={current_request_str} ({current_request_m}m), "
          f"limits={current_limit_str} ({current_limit_m}m)")
    
    # Only update if values have changed
    if cpu_limit_m == current_limit_m and cpu_request_m == current_request_m:
        print(f"  Resources already at target values, no update needed")
        return True
    
    patch = json.dumps({
        "spec": {
            "containers": [
                {
                    "name": container,
                    "resources": {
                        "limits": {
                            "cpu": f"{cpu_limit_m}m"
                        },
                        "requests": {
                            "cpu": f"{cpu_request_m}m"
                        }
                    }
                }
            ]
        }
    })
    
    # Use --subresource=resize to directly resize the pod without triggering a restart
    success, output = run_command([
        "kubectl", "patch", "pod", pod,
        "-n", NAMESPACE,
        "--subresource", "resize",
        "--type", "strategic",
        "-p", patch
    ])
    
    if success:
        print(f"  Updated CPU resources for pod {pod}, container {container}:")
        print(f"    Limits: {current_limit_m}m → {cpu_limit_m}m")
        print(f"    Requests: {current_request_m}m → {cpu_request_m}m")
        return True
    else:
        print(f"  Failed to update CPU resources: {output}")
        return False


def main():
    """Main controller loop"""
    print(f"Starting CPU controller with threshold={THRESHOLD*100}%, interval={INTERVAL}s")
    print(f"Monitoring services: {', '.join(SERVICES)}")
    print(f"Requests will be set to {REQUEST_RATIO*100}% of limits")
    print(f"Scale up factor: {SCALE_UP_FACTOR}, Scale down factor: {SCALE_DOWN_FACTOR}")
    print(f"Using --subresource resize for direct pod resizing without restarts")
    
    try:
        while True:
            print(f"\n--- Monitoring cycle at {time.strftime('%Y-%m-%d %H:%M:%S')} ---")
            
            for service in SERVICES:
                # Fetch fresh list of pods each time
                pods = get_pods_for_service(service)
                if not pods:
                    continue
                
                # Process each pod for this service
                for pod in pods:
                    # Get container name
                    container_name = get_container_for_pod(pod)
                    if not container_name:
                        print(f"  Could not find container for pod {pod}")
                        continue
                    
                    # Get CPU usage
                    cpu_usage_m = get_cpu_usage(pod)
                    if cpu_usage_m is None:
                        continue
                    
                    print(f"Service: {service}, Pod: {pod}, Container: {container_name}")
                    
                    # Get current resource settings
                    current_request_str, current_limit_str = get_current_pod_resources(pod, container_name)
                    current_limit_m = parse_cpu_value(current_limit_str) if current_limit_str else 100
                    
                    # Calculate current usage percentage
                    usage_percentage = (cpu_usage_m / current_limit_m) if current_limit_m > 0 else 1.0
                    print(f"  Current usage: {cpu_usage_m:.0f}m of {current_limit_m}m limit ({usage_percentage*100:.1f}%)")
                    
                    # Determine scaling direction based on threshold
                    new_limit_m = current_limit_m
                    if usage_percentage > THRESHOLD:
                        # Scale up
                        new_limit_m = int(current_limit_m * SCALE_UP_FACTOR)
                        print(f"  Usage above threshold ({THRESHOLD*100}%), scaling UP")
                    else:
                        # Scale down (but not below actual usage)
                        min_limit = max(int(cpu_usage_m * 1.2), 50)  # Never go below usage + 20% buffer or 50m
                        potential_new_limit = int(current_limit_m * SCALE_DOWN_FACTOR)
                        new_limit_m = max(potential_new_limit, min_limit)
                        if new_limit_m < current_limit_m:
                            print(f"  Usage below threshold ({THRESHOLD*100}%), scaling DOWN")
                        else:
                            print(f"  Usage below threshold but at minimum reasonable limit, not scaling down")
                    
                    # Round to nearest 10m
                    new_limit_m = ((new_limit_m + 5) // 10) * 10
                    
                    # Update the CPU resources
                    resize_pod_cpu_resources(pod, container_name, new_limit_m)
            
            print(f"Sleeping for {INTERVAL} seconds...")
            time.sleep(INTERVAL)
            
    except KeyboardInterrupt:
        print("\nController stopped by user")


if __name__ == "__main__":
    main()