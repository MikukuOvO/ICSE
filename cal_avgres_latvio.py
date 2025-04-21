import csv
import datetime
from collections import defaultdict

def analyze_slo_violations(file_path):
    """
    Analyze SLO violations for home-timeline, compose-post, and user-timeline services
    and calculate average resource allocation during those periods.
    
    Args:
        file_path: Path to the CSV file with k8s resource data
    
    Returns:
        tuple: (slo_violations, avg_resources) dictionaries with analysis results
    """
    # Service names we're interested in
    services = ['home-timeline-service', 'compose-post-service', 'user-timeline-service']
    
    # Define SLO thresholds (ms)
    slo_thresholds = {
        'home-timeline': 200,
        'compose-post': 200,
        'user-timeline': 200
    }
    
    # Track violation periods
    violation_periods = {
        'home-timeline': [],
        'compose-post': [],
        'user-timeline': []
    }
    
    # Track resources for all time periods
    resources_all_time = {
        'home-timeline': {'cpu_requests': [], 'mem_requests': [], 'cpu_usage': [], 'mem_usage': []},
        'compose-post': {'cpu_requests': [], 'mem_requests': [], 'cpu_usage': [], 'mem_usage': []},
        'user-timeline': {'cpu_requests': [], 'mem_requests': [], 'cpu_usage': [], 'mem_usage': []}
    }
    
    # For tracking current violation state
    current_violations = {
        'home-timeline': {'start': None, 'ongoing': False},
        'compose-post': {'start': None, 'ongoing': False},
        'user-timeline': {'start': None, 'ongoing': False}
    }
    
    # Parse the CSV file
    with open(file_path, 'r') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            timestamp = datetime.datetime.strptime(row['timestamp'], '%Y-%m-%d %H:%M:%S')
            
            # Check for violations in each service
            for service_base in ['home-timeline', 'compose-post', 'user-timeline']:
                service = f"{service_base}-service"
                
                # Find and check latency fields for the service
                latency_value = None
                
                # For compose-post service
                if service_base == 'compose-post':
                    field = f"{service_base}-service-latency_{service}"
                    if field in row and row[field] not in ['nan', 'N/A', '']:
                        try:
                            latency_value = float(row[field])
                        except (ValueError, TypeError):
                            latency_value = None
                
                # For home-timeline service, check both read and write latency
                elif service_base == 'home-timeline':
                    read_field = f"{service_base}-service-read-latency_{service}"
                    write_field = f"{service_base}-service-write-latency_{service}"
                    
                    read_latency = None
                    write_latency = None
                    
                    if read_field in row and row[read_field] not in ['nan', 'N/A', '']:
                        try:
                            read_latency = float(row[read_field])
                        except (ValueError, TypeError):
                            pass
                    
                    if write_field in row and row[write_field] not in ['nan', 'N/A', '']:
                        try:
                            write_latency = float(row[write_field])
                        except (ValueError, TypeError):
                            pass
                    
                    # Take the maximum of read and write latency if both exist
                    if read_latency is not None and write_latency is not None:
                        latency_value = max(read_latency, write_latency)
                    elif read_latency is not None:
                        latency_value = read_latency
                    elif write_latency is not None:
                        latency_value = write_latency
                
                # For user-timeline service, check both read and write latency
                elif service_base == 'user-timeline':
                    read_field = f"{service_base}-service-read-latency_{service}"
                    write_field = f"{service_base}-service-write-latency_{service}"
                    
                    read_latency = None
                    write_latency = None
                    
                    if read_field in row and row[read_field] not in ['nan', 'N/A', '']:
                        try:
                            read_latency = float(row[read_field])
                        except (ValueError, TypeError):
                            pass
                    
                    if write_field in row and row[write_field] not in ['nan', 'N/A', '']:
                        try:
                            write_latency = float(row[write_field])
                        except (ValueError, TypeError):
                            pass
                    
                    # Take the maximum of read and write latency if both exist
                    if read_latency is not None and write_latency is not None:
                        latency_value = max(read_latency, write_latency)
                    elif read_latency is not None:
                        latency_value = read_latency
                    elif write_latency is not None:
                        latency_value = write_latency
                
                # Always collect resource metrics for all time periods
                cpu_requests_field = f"cpu_requests_{service}"
                mem_requests_field = f"mem_requests_{service}"
                cpu_usage_field = f"cpu_usage_{service}"
                mem_usage_field = f"mem_usage_{service}"
                
                # Collect resource values for all time if they exist in the row
                if cpu_requests_field in row and row[cpu_requests_field] not in ['nan', 'N/A', '']:
                    resources_all_time[service_base]['cpu_requests'].append(row[cpu_requests_field])
                if mem_requests_field in row and row[mem_requests_field] not in ['nan', 'N/A', '']:
                    resources_all_time[service_base]['mem_requests'].append(row[mem_requests_field])
                if cpu_usage_field in row and row[cpu_usage_field] not in ['nan', 'N/A', '']:
                    resources_all_time[service_base]['cpu_usage'].append(row[cpu_usage_field])
                if mem_usage_field in row and row[mem_usage_field] not in ['nan', 'N/A', '']:
                    resources_all_time[service_base]['mem_usage'].append(row[mem_usage_field])
                
                # Check for SLO violation
                is_violating = False
                if latency_value is not None and latency_value > slo_thresholds[service_base]:
                    is_violating = True
                
                # Track violation periods
                if is_violating:
                    # Check if this is the start of a new violation period
                    if not current_violations[service_base]['ongoing']:
                        current_violations[service_base]['start'] = timestamp
                        current_violations[service_base]['ongoing'] = True
                else:
                    # Check if we need to end a violation period
                    if current_violations[service_base]['ongoing']:
                        # Calculate duration of violation
                        start_time = current_violations[service_base]['start']
                        duration = (timestamp - start_time).total_seconds()
                        
                        # Add to violation periods
                        violation_periods[service_base].append({
                            'start': start_time,
                            'end': timestamp,
                            'duration_seconds': duration
                        })
                        
                        # Reset violation state
                        current_violations[service_base]['ongoing'] = False
                        current_violations[service_base]['start'] = None
    
    # Close any ongoing violations at the end of the data
    for service_base in ['home-timeline', 'compose-post', 'user-timeline']:
        if current_violations[service_base]['ongoing']:
            # Use the last timestamp as the end time
            start_time = current_violations[service_base]['start']
            duration = (timestamp - start_time).total_seconds()
            
            # Add to violation periods
            violation_periods[service_base].append({
                'start': start_time,
                'end': timestamp,
                'duration_seconds': duration
            })
    
    # Calculate average resource metrics for all time
    avg_resources_all_time = {}
    
    for service_base in ['home-timeline', 'compose-post', 'user-timeline']:
        avg_resources_all_time[service_base] = {
            'cpu_requests': 'N/A',
            'mem_requests': 'N/A',
            'cpu_usage': 'N/A',
            'mem_usage': 'N/A'
        }
        
        # Function to calculate average for resources with suffixes
        def calculate_resource_avg(values, suffix):
            if not values:
                return 'N/A'
                
            # Extract numerical values
            numeric_values = []
            for val in values:
                if isinstance(val, str) and val.endswith(suffix):
                    try:
                        numeric_values.append(float(val[:-len(suffix)]))
                    except ValueError:
                        pass
            
            if numeric_values:
                avg_value = sum(numeric_values) / len(numeric_values)
                return f"{avg_value:.2f}{suffix}"
            return 'N/A'
        
        # Calculate averages for all resource types
        avg_resources_all_time[service_base]['cpu_requests'] = calculate_resource_avg(
            resources_all_time[service_base]['cpu_requests'], 'm')
        
        avg_resources_all_time[service_base]['mem_requests'] = calculate_resource_avg(
            resources_all_time[service_base]['mem_requests'], 'Mi')
            
        avg_resources_all_time[service_base]['cpu_usage'] = calculate_resource_avg(
            resources_all_time[service_base]['cpu_usage'], 'm')
            
        avg_resources_all_time[service_base]['mem_usage'] = calculate_resource_avg(
            resources_all_time[service_base]['mem_usage'], 'Mi')
    
    return violation_periods, avg_resources_all_time

def main():
    # Path to the CSV file
    file_path = 'k8s_resources.csv'  # Change this to your actual file path
    
    # Analyze SLO violations and resource allocation
    violation_periods, avg_resources = analyze_slo_violations(file_path)
    
    # Print results
    print("SLO Violation Analysis\n")
    print("======================\n")
    
    for service in ['home-timeline', 'compose-post', 'user-timeline']:
        print(f"\n{service} Service:")
        print("-" * (len(service) + 9))
        
        if not violation_periods[service]:
            print("No SLO violations detected.")
        else:
            total_duration = sum(period['duration_seconds'] for period in violation_periods[service])
            print(f"Total violation periods: {len(violation_periods[service])}")
            print(f"Total violation duration: {total_duration:.2f} seconds")
            
            print("\nViolation Periods:")
            for i, period in enumerate(violation_periods[service]):
                print(f"  {i+1}. Start: {period['start']}, End: {period['end']}, Duration: {period['duration_seconds']:.2f}s")
        
        print("\nAverage Resource Allocation (All Time):")
        print(f"  CPU Requests: {avg_resources[service]['cpu_requests']}")
        print(f"  Memory Requests: {avg_resources[service]['mem_requests']}")
        print(f"  CPU Usage: {avg_resources[service]['cpu_usage']}")
        print(f"  Memory Usage: {avg_resources[service]['mem_usage']}")
        print("\n" + "=" * 50)

if __name__ == "__main__":
    main()