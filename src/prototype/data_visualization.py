import matplotlib.pyplot as plt
import numpy as np

def create_service_figures(timestamps, service_data):
    """
    Create and save figures showing resource usage for all services
    """
    # Get all unique services and pods
    all_services = {}  # Dictionary to map service name to list of pods
    
    for time_point in service_data:
        for service_name, service_info in time_point['services'].items():
            if service_name not in all_services:
                all_services[service_name] = []
            
            for pod in service_info['pods']:
                if pod['name'] not in all_services[service_name]:
                    all_services[service_name].append(pod['name'])
    
    # Create a color map for services
    service_names = sorted(all_services.keys())
    service_colors = plt.cm.tab10(np.linspace(0, 1, len(service_names)))
    service_color_map = {service: service_colors[i] for i, service in enumerate(service_names)}
    
    # Prepare time axis (minutes elapsed)
    start_time = service_data[0]['time']
    minutes_elapsed = [(point['time'] - start_time).total_seconds() / 60 for point in service_data]
    
    # Create overview figures for all services
    create_service_overview_figures(service_names, service_color_map, service_data, minutes_elapsed)
    
    # Create detailed figures for home-timeline-service (the one with VPA)
    if 'home-timeline-service' in service_names:
        create_detailed_metrics_figures('home-timeline-service', service_data, minutes_elapsed)
    
    # Print statistics for all services
    print_service_statistics(all_services, service_data)

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

def create_service_overview_figures(service_names, service_color_map, service_data, minutes_elapsed):
    """
    Create overview figures showing aggregated metrics for all services
    """
    # Create a figure for CPU usage per service (aggregated)
    plt.figure(figsize=(15, 10))
    
    for service_name in service_names:
        # For each service, aggregate CPU usage across all pods
        service_cpu_usage = []
        
        for i, time_point in enumerate(service_data):
            if service_name in time_point['services']:
                service_info = time_point['services'][service_name]
                
                # Sum CPU usage for all pods in this service at this time point
                total_usage = 0
                valid_pods = 0
                
                for pod in service_info['pods']:
                    if pod['cpu_usage'] is not None:
                        total_usage += pod['cpu_usage']
                        valid_pods += 1
                
                if valid_pods > 0:
                    service_cpu_usage.append((minutes_elapsed[i], total_usage))
        
        # Plot the aggregated CPU usage for this service
        if service_cpu_usage:
            x_values = [item[0] for item in service_cpu_usage]
            y_values = [item[1] for item in service_cpu_usage]
            plt.plot(x_values, y_values, '-o', label=service_name, color=service_color_map[service_name])
    
    # Plot VPA recommendations for home-timeline-service if available
    vpa_recs = []
    for i, time_point in enumerate(service_data):
        if 'vpa_recommendation' in time_point:
            vpa_rec = time_point['vpa_recommendation']
            try:
                # Convert to millicores
                vpa_recs.append((minutes_elapsed[i], convert_cpu_to_millicores(vpa_rec)))
            except (ValueError, TypeError) as e:
                print(f"Error converting VPA CPU recommendation '{vpa_rec}': {e}")
    
    if vpa_recs:
        vpa_x = [item[0] for item in vpa_recs]
        vpa_y = [item[1] for item in vpa_recs]
        plt.plot(vpa_x, vpa_y, '--', linewidth=3, color='black', label='VPA CPU Recommendation')
    
    plt.title('Total CPU Usage per Service Over Time')
    plt.xlabel('Time Elapsed (minutes)')
    plt.ylabel('CPU Usage (millicores)')
    plt.grid(True)
    plt.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=3)
    plt.tight_layout()
    plt.savefig('service_cpu_usage.png', bbox_inches='tight')
    print("\nService CPU Usage figure saved as 'service_cpu_usage.png'")
    
    # Create a figure for Memory usage per service (aggregated)
    plt.figure(figsize=(15, 10))
    
    for service_name in service_names:
        # For each service, aggregate Memory usage across all pods
        service_memory_usage = []
        
        for i, time_point in enumerate(service_data):
            if service_name in time_point['services']:
                service_info = time_point['services'][service_name]
                
                # Sum Memory usage for all pods in this service at this time point
                total_usage = 0
                valid_pods = 0
                
                for pod in service_info['pods']:
                    if pod['memory_usage'] is not None:
                        total_usage += pod['memory_usage']
                        valid_pods += 1
                
                if valid_pods > 0:
                    service_memory_usage.append((minutes_elapsed[i], total_usage))
        
        # Plot the aggregated Memory usage for this service
        if service_memory_usage:
            x_values = [item[0] for item in service_memory_usage]
            y_values = [item[1] for item in service_memory_usage]
            plt.plot(x_values, y_values, '-o', label=service_name, color=service_color_map[service_name])
    
    # Plot VPA memory recommendations if available
    vpa_mem_recs = []
    for i, time_point in enumerate(service_data):
        if 'vpa_memory_recommendation' in time_point:
            vpa_rec = time_point['vpa_memory_recommendation']
            try:
                # Convert to MiB using the helper function
                vpa_mem_recs.append((minutes_elapsed[i], convert_memory_to_mib(vpa_rec)))
            except (ValueError, TypeError) as e:
                print(f"Error converting VPA memory recommendation '{vpa_rec}': {e}")
    
    if vpa_mem_recs:
        vpa_x = [item[0] for item in vpa_mem_recs]
        vpa_y = [item[1] for item in vpa_mem_recs]
        plt.plot(vpa_x, vpa_y, '--', linewidth=3, color='black', label='VPA Memory Recommendation')
    
    plt.title('Total Memory Usage per Service Over Time')
    plt.xlabel('Time Elapsed (minutes)')
    plt.ylabel('Memory Usage (MiB)')
    plt.grid(True)
    plt.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=3)
    plt.tight_layout()
    plt.savefig('service_memory_usage.png', bbox_inches='tight')
    print("\nService Memory Usage figure saved as 'service_memory_usage.png'")
    
    # Create a figure for CPU Requests per service (aggregated)
    plt.figure(figsize=(15, 10))
    
    for service_name in service_names:
        # For each service, aggregate CPU requests across all pods
        service_cpu_requests = []
        
        for i, time_point in enumerate(service_data):
            if service_name in time_point['services']:
                service_info = time_point['services'][service_name]
                
                # Sum CPU requests for all pods in this service at this time point
                total_requests = 0
                valid_pods = 0
                
                for pod in service_info['pods']:
                    if pod['cpu_request'] is not None:
                        total_requests += pod['cpu_request']
                        valid_pods += 1
                
                if valid_pods > 0:
                    service_cpu_requests.append((minutes_elapsed[i], total_requests))
        
        # Plot the aggregated CPU requests for this service
        if service_cpu_requests:
            x_values = [item[0] for item in service_cpu_requests]
            y_values = [item[1] for item in service_cpu_requests]
            plt.plot(x_values, y_values, '-o', label=service_name, color=service_color_map[service_name])
    
    plt.title('Total CPU Requests per Service Over Time')
    plt.xlabel('Time Elapsed (minutes)')
    plt.ylabel('CPU Requests (millicores)')
    plt.grid(True)
    plt.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=3)
    plt.tight_layout()
    plt.savefig('service_cpu_requests.png', bbox_inches='tight')
    print("\nService CPU Requests figure saved as 'service_cpu_requests.png'")
    
    # Create a figure for Memory Requests per service (aggregated)
    plt.figure(figsize=(15, 10))
    
    for service_name in service_names:
        # For each service, aggregate Memory requests across all pods
        service_memory_requests = []
        
        for i, time_point in enumerate(service_data):
            if service_name in time_point['services']:
                service_info = time_point['services'][service_name]
                
                # Sum Memory requests for all pods in this service at this time point
                total_requests = 0
                valid_pods = 0
                
                for pod in service_info['pods']:
                    if pod['memory_request'] is not None:
                        total_requests += pod['memory_request']
                        valid_pods += 1
                
                if valid_pods > 0:
                    service_memory_requests.append((minutes_elapsed[i], total_requests))
        
        # Plot the aggregated Memory requests for this service
        if service_memory_requests:
            x_values = [item[0] for item in service_memory_requests]
            y_values = [item[1] for item in service_memory_requests]
            plt.plot(x_values, y_values, '-o', label=service_name, color=service_color_map[service_name])
    
    plt.title('Total Memory Requests per Service Over Time')
    plt.xlabel('Time Elapsed (minutes)')
    plt.ylabel('Memory Requests (MiB)')
    plt.grid(True)
    plt.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=3)
    plt.tight_layout()
    plt.savefig('service_memory_requests.png', bbox_inches='tight')
    print("\nService Memory Requests figure saved as 'service_memory_requests.png'")
    
def create_detailed_metrics_figures(service_name, service_data, minutes_elapsed):
    """
    Create detailed metrics figures for a specific service (with VPA)
    """
    # Collect all pods for this service
    service_pods = set()
    for time_point in service_data:
        if service_name in time_point['services']:
            service_info = time_point['services'][service_name]
            for pod in service_info['pods']:
                service_pods.add(pod['name'])
    
    service_pods = sorted(list(service_pods))
    
    # Create a color map for pods
    pod_colors = plt.cm.tab10(np.linspace(0, 1, len(service_pods)))
    pod_color_map = {pod: pod_colors[i] for i, pod in enumerate(service_pods)}
    
    # Create a combined figure with all CPU metrics for comparison
    plt.figure(figsize=(15, 10))
    
    # Plot VPA recommendations if available
    vpa_recs = []
    for i, time_point in enumerate(service_data):
        if 'vpa_recommendation' in time_point:
            vpa_rec = time_point['vpa_recommendation']
            try:
                # Convert to millicores
                vpa_recs.append((minutes_elapsed[i], convert_cpu_to_millicores(vpa_rec)))
            except (ValueError, TypeError) as e:
                print(f"Error converting VPA CPU recommendation '{vpa_rec}': {e}")
    
    if vpa_recs:
        vpa_x = [item[0] for item in vpa_recs]
        vpa_y = [item[1] for item in vpa_recs]
        plt.plot(vpa_x, vpa_y, '--', linewidth=3, color='black', label='VPA Recommendation')
    
    # Plot requests, limits and usage for each pod
    line_styles = ['-', '--', ':']
    
    for pod_name in service_pods:
        color = pod_color_map[pod_name]
        
        # Plot requests
        x_values = []
        y_values = []
        for i, time_point in enumerate(service_data):
            if service_name in time_point['services']:
                for pod in time_point['services'][service_name]['pods']:
                    if pod['name'] == pod_name and pod['cpu_request'] is not None:
                        x_values.append(minutes_elapsed[i])
                        y_values.append(pod['cpu_request'])
        if x_values:
            plt.plot(x_values, y_values, line_styles[0], color=color, alpha=0.7, 
                     label=f"{pod_name} (Request)")
        
        # Plot limits
        x_values = []
        y_values = []
        for i, time_point in enumerate(service_data):
            if service_name in time_point['services']:
                for pod in time_point['services'][service_name]['pods']:
                    if pod['name'] == pod_name and pod['cpu_limit'] is not None:
                        x_values.append(minutes_elapsed[i])
                        y_values.append(pod['cpu_limit'])
        if x_values:
            plt.plot(x_values, y_values, line_styles[1], color=color, alpha=0.7,
                     label=f"{pod_name} (Limit)")
        
        # Plot usage
        x_values = []
        y_values = []
        for i, time_point in enumerate(service_data):
            if service_name in time_point['services']:
                for pod in time_point['services'][service_name]['pods']:
                    if pod['name'] == pod_name and pod['cpu_usage'] is not None:
                        x_values.append(minutes_elapsed[i])
                        y_values.append(pod['cpu_usage'])
        if x_values:
            plt.plot(x_values, y_values, line_styles[2], color=color, alpha=0.9, 
                     label=f"{pod_name} (Usage)")
    
    plt.title(f'{service_name} - CPU Metrics Comparison: Requests, Limits, Usage, and VPA Recommendations')
    plt.xlabel('Time Elapsed (minutes)')
    plt.ylabel('CPU (millicores)')
    plt.grid(True)
    plt.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=3)
    plt.tight_layout()
    plt.savefig(f'{service_name}_cpu_all_metrics.png', bbox_inches='tight')
    print(f"\n{service_name} CPU metrics figure saved as '{service_name}_cpu_all_metrics.png'")
    
    # Create a combined figure with all Memory metrics for comparison
    plt.figure(figsize=(15, 10))
    
    # Plot VPA memory recommendations if available
    vpa_mem_recs = []
    for i, time_point in enumerate(service_data):
        if 'vpa_memory_recommendation' in time_point:
            vpa_rec = time_point['vpa_memory_recommendation']
            try:
                # Convert to MiB using the helper function
                vpa_mem_recs.append((minutes_elapsed[i], convert_memory_to_mib(vpa_rec)))
            except (ValueError, TypeError) as e:
                print(f"Error converting VPA memory recommendation '{vpa_rec}': {e}")
    
    if vpa_mem_recs:
        vpa_x = [item[0] for item in vpa_mem_recs]
        vpa_y = [item[1] for item in vpa_mem_recs]
        plt.plot(vpa_x, vpa_y, '--', linewidth=3, color='black', label='VPA Memory Recommendation')
    
    # Plot requests, limits and usage for each pod
    for pod_name in service_pods:
        color = pod_color_map[pod_name]
        
        # Plot requests
        x_values = []
        y_values = []
        for i, time_point in enumerate(service_data):
            if service_name in time_point['services']:
                for pod in time_point['services'][service_name]['pods']:
                    if pod['name'] == pod_name and pod['memory_request'] is not None:
                        x_values.append(minutes_elapsed[i])
                        y_values.append(pod['memory_request'])
        if x_values:
            plt.plot(x_values, y_values, line_styles[0], color=color, alpha=0.7, 
                     label=f"{pod_name} (Request)")
        
        # Plot limits
        x_values = []
        y_values = []
        for i, time_point in enumerate(service_data):
            if service_name in time_point['services']:
                for pod in time_point['services'][service_name]['pods']:
                    if pod['name'] == pod_name and pod['memory_limit'] is not None:
                        x_values.append(minutes_elapsed[i])
                        y_values.append(pod['memory_limit'])
        if x_values:
            plt.plot(x_values, y_values, line_styles[1], color=color, alpha=0.7,
                     label=f"{pod_name} (Limit)")
        
        # Plot usage
        x_values = []
        y_values = []
        for i, time_point in enumerate(service_data):
            if service_name in time_point['services']:
                for pod in time_point['services'][service_name]['pods']:
                    if pod['name'] == pod_name and pod['memory_usage'] is not None:
                        x_values.append(minutes_elapsed[i])
                        y_values.append(pod['memory_usage'])
        if x_values:
            plt.plot(x_values, y_values, line_styles[2], color=color, alpha=0.9, 
                     label=f"{pod_name} (Usage)")
    
    plt.title(f'{service_name} - Memory Metrics Comparison: Requests, Limits, Usage, and VPA Recommendations')
    plt.xlabel('Time Elapsed (minutes)')
    plt.ylabel('Memory (MiB)')
    plt.grid(True)
    plt.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=3)
    plt.tight_layout()
    plt.savefig(f'{service_name}_memory_all_metrics.png', bbox_inches='tight')
    print(f"\n{service_name} Memory metrics figure saved as '{service_name}_memory_all_metrics.png'")

def print_service_statistics(all_services, service_data):
    """
    Print resource usage statistics for all services and pods
    """
    print("\nPer-Service Statistics:")
    for service_name, pod_names in all_services.items():
        print(f"\n  Service: {service_name}")
        
        # Collect CPU and Memory usage statistics for each pod
        for pod_name in pod_names:
            all_cpu_requests = []
            all_cpu_limits = []
            all_cpu_usage = []
            all_memory_requests = []
            all_memory_limits = []
            all_memory_usage = []
            
            for time_point in service_data:
                if service_name in time_point['services']:
                    service_info = time_point['services'][service_name]
                    for pod in service_info['pods']:
                        if pod['name'] == pod_name:
                            if pod['cpu_request'] is not None:
                                all_cpu_requests.append(pod['cpu_request'])
                            if pod['cpu_limit'] is not None:
                                all_cpu_limits.append(pod['cpu_limit'])
                            if pod['cpu_usage'] is not None:
                                all_cpu_usage.append(pod['cpu_usage'])
                            if pod['memory_request'] is not None:
                                all_memory_requests.append(pod['memory_request'])
                            if pod['memory_limit'] is not None:
                                all_memory_limits.append(pod['memory_limit'])
                            if pod['memory_usage'] is not None:
                                all_memory_usage.append(pod['memory_usage'])
            
            print(f"\n    Pod: {pod_name}")
            
            # Print CPU statistics if we have data
            if all_cpu_requests:
                print(f"      CPU Request: Initial={all_cpu_requests[0]}m, Final={all_cpu_requests[-1]}m, Min={min(all_cpu_requests)}m, Max={max(all_cpu_requests)}m")
            
            if all_cpu_limits:
                print(f"      CPU Limit: Initial={all_cpu_limits[0]}m, Final={all_cpu_limits[-1]}m, Min={min(all_cpu_limits)}m, Max={max(all_cpu_limits)}m")
            
            if all_cpu_usage:
                print(f"      CPU Usage: Min={min(all_cpu_usage)}m, Max={max(all_cpu_usage)}m, Avg={sum(all_cpu_usage)/len(all_cpu_usage):.2f}m")
            
            # Print Memory statistics if we have data
            if all_memory_requests:
                print(f"      Memory Request: Initial={all_memory_requests[0]}Mi, Final={all_memory_requests[-1]}Mi, Min={min(all_memory_requests)}Mi, Max={max(all_memory_requests)}Mi")
            
            if all_memory_limits:
                print(f"      Memory Limit: Initial={all_memory_limits[0]}Mi, Final={all_memory_limits[-1]}Mi, Min={min(all_memory_limits)}Mi, Max={max(all_memory_limits)}Mi")
            
            if all_memory_usage:
                print(f"      Memory Usage: Min={min(all_memory_usage)}Mi, Max={max(all_memory_usage)}Mi, Avg={sum(all_memory_usage)/len(all_memory_usage):.2f}Mi")
                
        # VPA recommendation statistics if available
        if service_name == 'home-timeline-service':
            vpa_cpu_recs = []
            vpa_memory_recs = []
            
            for time_point in service_data:
                if 'vpa_recommendation' in time_point:
                    try:
                        vpa_rec = time_point['vpa_recommendation']
                        # Convert to millicores
                        vpa_cpu_recs.append(convert_cpu_to_millicores(vpa_rec))
                    except (ValueError, TypeError) as e:
                        print(f"Error processing VPA CPU recommendation '{vpa_rec}': {e}")
                
                if 'vpa_memory_recommendation' in time_point:
                    try:
                        vpa_rec = time_point['vpa_memory_recommendation']
                        # Convert to MiB
                        vpa_memory_recs.append(convert_memory_to_mib(vpa_rec))
                    except (ValueError, TypeError) as e:
                        print(f"Error processing VPA memory recommendation '{vpa_rec}': {e}")
            
            if vpa_cpu_recs:
                print(f"\n    VPA CPU Recommendation: Initial={vpa_cpu_recs[0]}m, Final={vpa_cpu_recs[-1]}m, Min={min(vpa_cpu_recs)}m, Max={max(vpa_cpu_recs)}m, Avg={sum(vpa_cpu_recs)/len(vpa_cpu_recs):.2f}m")
            
            if vpa_memory_recs:
                print(f"    VPA Memory Recommendation: Initial={vpa_memory_recs[0]:.2f}Mi, Final={vpa_memory_recs[-1]:.2f}Mi, Min={min(vpa_memory_recs):.2f}Mi, Max={max(vpa_memory_recs):.2f}Mi, Avg={sum(vpa_memory_recs)/len(vpa_memory_recs):.2f}Mi")