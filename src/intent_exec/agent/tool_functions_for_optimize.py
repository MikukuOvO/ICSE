@with_requirements(python_packages=['subprocess'], global_imports=[])
def set_service_cpu(namespace: str, service: str, cpu_cores: float) -> str:
    """
    This function sets the CPU resource allocation (both request and limit) for a specific service 
    in a Kubernetes namespace to a target value using kubectl.
    
    - param namespace: str, the Kubernetes namespace where the service is deployed
    - param service: str, the name of the service to adjust resources for
    - param cpu_cores: float, the target CPU cores to set (absolute value)
    
    - return: str, the result of the operation
    
    Note: 
    - ALWAYS call print() to report the result so that planner can get the result.
    - This function updates both CPU request and limit with the same value.
    - CPU resources in Kubernetes are measured in cores, where 1.0 represents one full CPU core.
    - The minimum allowed value is 50m (0.05) cores and maximum is 800m (0.8) cores.
    - The function checks if the change is significant (> 1/2 of current allocation) before applying.
    
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
    import re
    
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
    
    # Get current CPU allocation using kubectl describe
    try:
        cmd = f"kubectl describe deployment {target_deployment} -n {namespace}"
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        deployment_desc = result.stdout
        
        # Extract CPU limits using regex
        cpu_limits_pattern = r"Limits:\s+cpu:\s+(\d+)m|Limits:\s+cpu:\s+(\d+(?:\.\d+)?)"
        cpu_limits_match = re.search(cpu_limits_pattern, deployment_desc)
        
        current_cpu = None
        if cpu_limits_match:
            # Check which group matched (millicore or core format)
            if cpu_limits_match.group(1):  # millicore format (e.g. 500m)
                current_cpu = float(cpu_limits_match.group(1)) / 1000
            elif cpu_limits_match.group(2):  # core format (e.g. 0.5)
                current_cpu = float(cpu_limits_match.group(2))
        
        if current_cpu is None:
            return f"Error: Could not determine current CPU allocation for deployment '{target_deployment}'"
        
        # Calculate delta and check if change is significant
        delta = abs(cpu_cores - current_cpu)
        if delta > (current_cpu / 2):
            return f"Error: The change in CPU allocation ({delta:.3f} cores) is too large (must be <= {current_cpu/2:.3f} cores, which is 1/2 of the current allocation of {current_cpu:.3f} cores)"        
    
    except subprocess.CalledProcessError as e:
        return f"Error getting current CPU allocation: {e.stderr}"
    
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
    
    return f"CPU resources for service '{service}' in namespace '{namespace}' changed from {current_cpu} to {cpu_cores} cores."