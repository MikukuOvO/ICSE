from .utils import convert_cpu_to_millicores, convert_memory_to_mib, safe_convert

def export_service_data_csv(timestamps, service_data):
    """
    Export all service data to a CSV file for further analysis
    """
    csv_file = "service_resource_data.csv"
    
    # Get all unique services and pods
    all_services = set()
    all_pods = set()
    
    for time_point in service_data:
        for service_name, service_info in time_point['services'].items():
            all_services.add(service_name)
            for pod in service_info['pods']:
                all_pods.add(pod['name'])
    
    all_services = sorted(list(all_services))
    all_pods = sorted(list(all_pods))
    
    # Prepare CSV header
    header = ["Timestamp", "Elapsed_Minutes"]
    
    # Add columns for each pod's metrics
    for pod_name in all_pods:
        header.extend([
            f"{pod_name}_CPU_Request", 
            f"{pod_name}_CPU_Limit", 
            f"{pod_name}_CPU_Usage",
            f"{pod_name}_Memory_Request", 
            f"{pod_name}_Memory_Limit", 
            f"{pod_name}_Memory_Usage"
        ])
    
    # Add VPA recommendation columns
    header.extend(["VPA_CPU_Recommendation", "VPA_Memory_Recommendation"])
    
    # Prepare CSV rows
    rows = []
    for i, time_point in enumerate(service_data):
        elapsed_minutes = (time_point['time'] - service_data[0]['time']).total_seconds() / 60
        
        row = [time_point['time'].strftime("%Y-%m-%d %H:%M:%S"), f"{elapsed_minutes:.2f}"]
        
        # Create a flat dictionary of all pods from all services for this time point
        pod_dict = {}
        for service_name, service_info in time_point['services'].items():
            for pod in service_info['pods']:
                pod_dict[pod['name']] = pod
        
        # Add data for each pod
        for pod_name in all_pods:
            if pod_name in pod_dict:
                pod = pod_dict[pod_name]
                row.extend([
                    pod['cpu_request'] if pod['cpu_request'] is not None else "",
                    pod['cpu_limit'] if pod['cpu_limit'] is not None else "",
                    pod['cpu_usage'] if pod['cpu_usage'] is not None else "",
                    pod['memory_request'] if pod['memory_request'] is not None else "",
                    pod['memory_limit'] if pod['memory_limit'] is not None else "",
                    pod['memory_usage'] if pod['memory_usage'] is not None else ""
                ])
            else:
                row.extend(["", "", "", "", "", ""])
        
        # Add VPA recommendations
        vpa_cpu_rec = ""
        if 'vpa_recommendation' in time_point:
            try:
                vpa_cpu_rec = safe_convert(convert_cpu_to_millicores, time_point['vpa_recommendation'], "")
            except Exception as e:
                print(f"Error processing VPA CPU recommendation: {e}")
        
        vpa_mem_rec = ""
        if 'vpa_memory_recommendation' in time_point:
            try:
                vpa_mem_rec = safe_convert(convert_memory_to_mib, time_point['vpa_memory_recommendation'], "")
            except Exception as e:
                print(f"Error processing VPA memory recommendation: {e}")
                
        row.append(vpa_cpu_rec)
        row.append(vpa_mem_rec)
        
        rows.append(row)
    
    # Write to CSV
    with open(csv_file, 'w') as f:
        # Write header
        f.write(",".join(header) + "\n")
        
        # Write rows
        for row in rows:
            f.write(",".join([str(cell) for cell in row]) + "\n")
    
    print(f"\nService resource data exported to {csv_file}")

    # Also export a summary of requests, limits and usage for each service and pod
    export_service_summary(service_data)

def export_service_summary(service_data):
    """
    Export a summary of resource usage statistics for all services and pods
    """
    summary_file = "service_resource_summary.csv"
    
    # Get all unique services and pods
    all_services = {}  # Dictionary to map service name to list of pods
    
    for time_point in service_data:
        for service_name, service_info in time_point['services'].items():
            if service_name not in all_services:
                all_services[service_name] = set()
            
            for pod in service_info['pods']:
                all_services[service_name].add(pod['name'])
    
    # Convert pod sets to sorted lists
    for service_name in all_services:
        all_services[service_name] = sorted(list(all_services[service_name]))
    
    # Prepare CSV header
    header = ["Service", "Pod", 
              "Initial_CPU_Request", "Final_CPU_Request", "Min_CPU_Request", "Max_CPU_Request",
              "Initial_CPU_Limit", "Final_CPU_Limit", "Min_CPU_Limit", "Max_CPU_Limit",
              "Min_CPU_Usage", "Max_CPU_Usage", "Avg_CPU_Usage",
              "Initial_Memory_Request", "Final_Memory_Request", "Min_Memory_Request", "Max_Memory_Request",
              "Initial_Memory_Limit", "Final_Memory_Limit", "Min_Memory_Limit", "Max_Memory_Limit",
              "Min_Memory_Usage", "Max_Memory_Usage", "Avg_Memory_Usage"]
    
    # Prepare CSV rows
    rows = []
    
    for service_name, pod_names in all_services.items():
        for pod_name in pod_names:
            # Collect all requests, limits, and usage values for this pod
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
            
            # Prepare row with statistics
            row = [service_name, pod_name]
            
            # Add CPU statistics
            if all_cpu_requests:
                row.extend([
                    all_cpu_requests[0],
                    all_cpu_requests[-1],
                    min(all_cpu_requests),
                    max(all_cpu_requests)
                ])
            else:
                row.extend(["", "", "", ""])
            
            if all_cpu_limits:
                row.extend([
                    all_cpu_limits[0],
                    all_cpu_limits[-1],
                    min(all_cpu_limits),
                    max(all_cpu_limits)
                ])
            else:
                row.extend(["", "", "", ""])
            
            if all_cpu_usage:
                row.extend([
                    min(all_cpu_usage),
                    max(all_cpu_usage),
                    sum(all_cpu_usage) / len(all_cpu_usage)
                ])
            else:
                row.extend(["", "", ""])
            
            # Add Memory statistics
            if all_memory_requests:
                row.extend([
                    all_memory_requests[0],
                    all_memory_requests[-1],
                    min(all_memory_requests),
                    max(all_memory_requests)
                ])
            else:
                row.extend(["", "", "", ""])
            
            if all_memory_limits:
                row.extend([
                    all_memory_limits[0],
                    all_memory_limits[-1],
                    min(all_memory_limits),
                    max(all_memory_limits)
                ])
            else:
                row.extend(["", "", "", ""])
            
            if all_memory_usage:
                row.extend([
                    min(all_memory_usage),
                    max(all_memory_usage),
                    sum(all_memory_usage) / len(all_memory_usage)
                ])
            else:
                row.extend(["", "", ""])
            
            rows.append(row)
        
        # Add VPA recommendation statistics if available for this service
        if service_name == 'home-timeline-service':
            vpa_cpu_recs = []
            vpa_memory_recs = []
            
            for time_point in service_data:
                if 'vpa_recommendation' in time_point:
                    try:
                        vpa_rec = time_point['vpa_recommendation']
                        # Convert to millicores
                        value = safe_convert(convert_cpu_to_millicores, vpa_rec)
                        if value is not None:
                            vpa_cpu_recs.append(value)
                    except Exception as e:
                        print(f"Error processing VPA CPU recommendation '{vpa_rec}': {e}")
                
                if 'vpa_memory_recommendation' in time_point:
                    try:
                        vpa_rec = time_point['vpa_memory_recommendation']
                        # Convert to MiB
                        value = safe_convert(convert_memory_to_mib, vpa_rec)
                        if value is not None:
                            vpa_memory_recs.append(value)
                    except Exception as e:
                        print(f"Error processing VPA memory recommendation '{vpa_rec}': {e}")
            
            if vpa_cpu_recs:
                row = [service_name, "VPA_CPU_Recommendation", 
                       vpa_cpu_recs[0], vpa_cpu_recs[-1], min(vpa_cpu_recs), max(vpa_cpu_recs)]
                # Fill remaining columns with empty strings
                row.extend([""] * (len(header) - len(row)))
                rows.append(row)
            
            if vpa_memory_recs:
                row = [service_name, "VPA_Memory_Recommendation", 
                       "", "", "", "", "", "", "",  # Skip CPU columns
                       vpa_memory_recs[0], vpa_memory_recs[-1], min(vpa_memory_recs), max(vpa_memory_recs)]
                # Fill remaining columns with empty strings
                row.extend([""] * (len(header) - len(row)))
                rows.append(row)
    
    # Write to CSV
    with open(summary_file, 'w') as f:
        # Write header
        f.write(",".join(header) + "\n")
        
        # Write rows
        for row in rows:
            f.write(",".join([str(cell) for cell in row]) + "\n")
    
    print(f"Service resource summary exported to {summary_file}")

def export_with_vpa_comparison(service_data):
    """
    Export a CSV specifically focused on comparing VPA recommendations with actual resource usage
    """
    vpa_comparison_file = "vpa_comparison.csv"
    service_name = 'home-timeline-service'  # The service with VPA
    
    header = ["Timestamp", "Elapsed_Minutes", 
              "Total_CPU_Usage", "VPA_CPU_Recommendation", "CPU_Usage_Ratio",
              "Total_Memory_Usage", "VPA_Memory_Recommendation", "Memory_Usage_Ratio"]
    
    rows = []
    for i, time_point in enumerate(service_data):
        if service_name not in time_point['services']:
            continue
            
        elapsed_minutes = (time_point['time'] - service_data[0]['time']).total_seconds() / 60
        row = [time_point['time'].strftime("%Y-%m-%d %H:%M:%S"), f"{elapsed_minutes:.2f}"]
        
        # Calculate total CPU usage for the service
        total_cpu_usage = 0
        valid_cpu_pods = 0
        
        for pod in time_point['services'][service_name]['pods']:
            if pod['cpu_usage'] is not None:
                total_cpu_usage += pod['cpu_usage']
                valid_cpu_pods += 1
        
        # Get VPA CPU recommendation
        vpa_cpu_rec = None
        if 'vpa_recommendation' in time_point:
            try:
                vpa_cpu_rec = safe_convert(convert_cpu_to_millicores, time_point['vpa_recommendation'])
            except Exception as e:
                print(f"Error processing VPA CPU recommendation: {e}")
        
        # Calculate usage ratio
        cpu_usage_ratio = ""
        if valid_cpu_pods > 0 and vpa_cpu_rec is not None:
            cpu_usage_ratio = f"{(total_cpu_usage / vpa_cpu_rec) * 100:.2f}%"
        
        row.extend([total_cpu_usage if valid_cpu_pods > 0 else "", 
                   vpa_cpu_rec if vpa_cpu_rec is not None else "",
                   cpu_usage_ratio])
        
        # Calculate total memory usage for the service
        total_memory_usage = 0
        valid_memory_pods = 0
        
        for pod in time_point['services'][service_name]['pods']:
            if pod['memory_usage'] is not None:
                total_memory_usage += pod['memory_usage']
                valid_memory_pods += 1
        
        # Get VPA memory recommendation
        vpa_memory_rec = None
        if 'vpa_memory_recommendation' in time_point:
            try:
                vpa_memory_rec = safe_convert(convert_memory_to_mib, time_point['vpa_memory_recommendation'])
            except Exception as e:
                print(f"Error processing VPA memory recommendation: {e}")
        
        # Calculate usage ratio
        memory_usage_ratio = ""
        if valid_memory_pods > 0 and vpa_memory_rec is not None:
            memory_usage_ratio = f"{(total_memory_usage / vpa_memory_rec) * 100:.2f}%"
        
        row.extend([total_memory_usage if valid_memory_pods > 0 else "", 
                   vpa_memory_rec if vpa_memory_rec is not None else "",
                   memory_usage_ratio])
        
        rows.append(row)
    
    # Write to CSV
    with open(vpa_comparison_file, 'w') as f:
        # Write header
        f.write(",".join(header) + "\n")
        
        # Write rows
        for row in rows:
            f.write(",".join([str(cell) for cell in row]) + "\n")
    
    print(f"VPA comparison data exported to {vpa_comparison_file}")