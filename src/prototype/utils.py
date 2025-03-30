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

def format_duration(seconds):
    """
    Format seconds into a human-readable duration
    """
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if hours > 0:
        return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
    elif minutes > 0:
        return f"{int(minutes)}m {int(seconds)}s"
    else:
        return f"{int(seconds)}s"

def get_pod_name_from_yaml(yaml_config, service_name):
    """
    Extract pod name pattern from YAML config
    """
    # This is a placeholder function - you would need to implement
    # the actual logic based on your YAML structure
    if 'deployments' in yaml_config and service_name in yaml_config['deployments']:
        deployment_info = yaml_config['deployments'][service_name]
        # Extract and return pod name pattern
        return deployment_info.get('pod_name_pattern', f"{service_name}-*")
    return f"{service_name}-*"  # Default pattern

def safe_convert(convert_func, value, default=None):
    """
    Safely convert a value using the provided conversion function
    Returns default value if conversion fails
    """
    try:
        if value is None:
            return default
        return convert_func(value)
    except (ValueError, TypeError) as e:
        print(f"Error converting value '{value}': {e}")
        return default