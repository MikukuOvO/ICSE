import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import os
import glob
import yaml

# Clear all CSV files from the output directory first
output_dir = 'service_visualizations'
os.makedirs(output_dir, exist_ok=True)
for csv_file in glob.glob(f"{output_dir}/*.csv"):
    os.remove(csv_file)
    print(f"Removed: {csv_file}")

# Clear all PNG files from the output directory as well
for png_file in glob.glob(f"{output_dir}/*.png"):
    os.remove(png_file)
    print(f"Removed: {png_file}")

# Read the data files
resource_data = pd.read_csv('k8s_resources.csv')
action_time_data = pd.read_csv('optimization_timing.csv')
locust_data = pd.read_csv('locust_results_stats_history.csv')

# Convert timestamp columns to datetime
resource_data['timestamp'] = pd.to_datetime(resource_data['timestamp'])
action_time_data['start_time'] = pd.to_datetime(action_time_data['start_time'])
action_time_data['end_time'] = pd.to_datetime(action_time_data['end_time'])

# Convert Unix timestamp in locust data to datetime
locust_data['datetime'] = pd.to_datetime(locust_data['Timestamp'], unit='s')

# Filter the locust data to only include 'Aggregated' requests for simplicity
# Create a proper copy to avoid SettingWithCopyWarning
aggregated_locust_data = locust_data[locust_data['Name'] == 'Aggregated'].copy()

# Select the columns we need and create a new DataFrame (not a view)
locust_workload_data = pd.DataFrame({
    'datetime': aggregated_locust_data['datetime'],
    'request_rate': aggregated_locust_data['Requests/s']
})

with open('src/conf/global_config.yaml', 'r') as f:
    global_config = yaml.safe_load(f)
    NAMESPACE = global_config.get('namespace', 'social-network')

# Load service from service_maintainers_optimize.yaml
with open('src/conf/service_maintainers_optimize.yaml', 'r') as f:
    service_config = yaml.safe_load(f)
    # Extract from deployment section with <NAMESPACE> as subsection
    target_services = service_config.get('deployments', {}).get(NAMESPACE, {})

# Updated function to convert resource strings to numeric values
def convert_resource_to_numeric(value):
    if isinstance(value, str):
        if value == 'N/A' or value == 'ERROR':
            return float('nan')
        elif value.endswith('m'):  # CPU: 100m = 0.1 cores
            return float(value.rstrip('m')) / 1000
        elif value.endswith('Mi'):  # Memory: 128Mi in MiB
            return float(value.rstrip('Mi'))
        elif value.endswith('Gi'):  # Memory: 1Gi = 1024 MiB
            return float(value.rstrip('Gi')) * 1024
    return value

# Process resource data
for column in resource_data.columns:
    if column != 'timestamp':
        # Process all resource-related columns (including usage)
        if (column.startswith('cpu_requests_') or column.startswith('mem_requests_') or 
            column.startswith('cpu_usage_') or column.startswith('mem_usage_')):
            resource_data[column] = resource_data[column].apply(convert_resource_to_numeric)

# Function to safely convert N/A values to NaN
def convert_na_to_nan(value):
    if isinstance(value, str) and (value == 'N/A' or value == 'ERROR'):
        return float('nan')
    return value

# Identify metric columns (only latency metrics as we'll use locust for workload)
metric_columns = [col for col in resource_data.columns 
                 if col != 'timestamp' 
                 and not col.startswith('cpu_requests_') 
                 and not col.startswith('mem_requests_')
                 and not col.startswith('cpu_usage_')
                 and not col.startswith('mem_usage_')]

# Process metric columns to ensure they're numeric
for column in metric_columns:
    resource_data[column] = resource_data[column].apply(convert_na_to_nan)
    resource_data[column] = pd.to_numeric(resource_data[column], errors='coerce')

# Use the closest timestamp in resource_data to merge with locust_workload_data
# First, create a function to find the closest timestamp
def find_closest_timestamp(target_time, time_series):
    return min(time_series, key=lambda x: abs(x - target_time))

# Create workload columns for each service in locust_workload_data
for service in target_services:
    # Using loc to properly set values and avoid SettingWithCopyWarning
    locust_workload_data.loc[:, f'request_rate_{service}'] = locust_workload_data['request_rate']

# Merge locust data with resource data based on closest timestamp
# This is a bit tricky since timestamps might not exactly match
# We'll use a merge_asof which is designed for this purpose
merged_data = pd.merge_asof(
    resource_data.sort_values('timestamp'),
    locust_workload_data.sort_values('datetime'),
    left_on='timestamp',
    right_on='datetime',
    direction='nearest'
)

# If merge_asof doesn't work well for your specific data, here's an alternative approach:
# This creates a new dataframe with all the same timestamps as resource_data
# but with the workload metrics from the closest timestamp in locust_data
if 'request_rate' not in merged_data.columns:
    print("Using alternative timestamp matching method...")
    # For each timestamp in resource_data, find the closest in locust_data
    for service in target_services:
        resource_data[f'request_rate_{service}'] = float('nan')
        resource_data[f'response_time_{service}'] = float('nan')
        
    for idx, row in resource_data.iterrows():
        if not locust_workload_data.empty:
            closest_idx = abs(locust_workload_data['datetime'] - row['timestamp']).idxmin()
            closest_row = locust_workload_data.loc[closest_idx]
            
            for service in target_services:
                resource_data.at[idx, f'request_rate_{service}'] = closest_row['request_rate']
    
    # Use resource_data as our merged_data
    merged_data = resource_data
else:
    # Add any missing columns to merged_data
    for service in target_services:
        if f'request_rate_{service}' not in merged_data.columns:
            merged_data[f'request_rate_{service}'] = merged_data['request_rate']

# Map services to their related metrics
service_to_metrics_map = {}
for service in target_services:
    # Find all metrics related to this service
    # With the new naming format, metrics will end with the service name
    related_metrics = [col for col in metric_columns if col.endswith(f"_{service}")]
    
    # Group metrics by type (only latency metrics from the original data)
    latency_metrics = [m for m in related_metrics if any(k in m.lower() for k in ['latency', 'duration', 'response_time'])]
    
    # Add our new workload metrics from locust (only using request rate)
    workload_metrics = [f'request_rate_{service}']
    
    # Not adding response_time as latency metric since existing latency metrics are already available
    
    service_to_metrics_map[service] = {
        'latency': latency_metrics,
        'workload': workload_metrics
    }

# Function to add action time vertical lines to a plot
def add_action_times(ax, action_time_data):
    for idx, row in action_time_data.iterrows():
        ax.axvline(x=row['start_time'], color='green', linestyle='--', alpha=0.7, 
                  label='Action Start' if idx == 0 else '')
        ax.axvline(x=row['end_time'], color='red', linestyle='--', alpha=0.7, 
                  label='Action End' if idx == 0 else '')

# Function to format time axis
def format_time_axis(ax):
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    for label in ax.get_xticklabels():
        label.set_rotation(45)
        label.set_ha('right')

# Create 1x4 figures for each service showing both requests and usage
for service in target_services:
    print(f"Processing service: {service}")
    
    # Get the columns for this service
    cpu_requests_col = f'cpu_requests_{service}'
    mem_requests_col = f'mem_requests_{service}'
    cpu_usage_col = f'cpu_usage_{service}'
    mem_usage_col = f'mem_usage_{service}'
    
    # Check if the service actually exists in the data
    if cpu_requests_col not in merged_data.columns or mem_requests_col not in merged_data.columns:
        print(f"Warning: {service} not found in resource data, skipping...")
        continue
        
    # Get related metrics for this service
    latency_metrics = service_to_metrics_map[service]['latency']
    workload_metrics = service_to_metrics_map[service]['workload']
    
    print(f"Found {len(latency_metrics)} latency metrics and {len(workload_metrics)} workload metrics for {service}")
    
    # --------------------- 1x4 Resource Dashboard Figure ---------------------
    fig, axes = plt.subplots(1, 4, figsize=(20, 5))  # 1 row, 4 columns
    fig.suptitle(f'Resource Dashboard for {service}', fontsize=16)
    
    # CPU Requests Plot
    axes[0].set_title('CPU Requests')
    axes[0].set_xlabel('Time')
    axes[0].set_ylabel('CPU Cores')
    axes[0].plot(merged_data['timestamp'], merged_data[cpu_requests_col], color='tab:blue', marker='o', label='CPU Requests')
    add_action_times(axes[0], action_time_data)
    format_time_axis(axes[0])
    axes[0].grid(True, linestyle='--', alpha=0.7)
    axes[0].legend()
    
    # CPU Usage Plot
    axes[1].set_title('CPU Usage')
    axes[1].set_xlabel('Time')
    axes[1].set_ylabel('CPU Cores')
    if cpu_usage_col in merged_data.columns:
        axes[1].plot(merged_data['timestamp'], merged_data[cpu_usage_col], color='tab:orange', marker='o', label='CPU Usage')
    else:
        axes[1].text(0.5, 0.5, 'No CPU usage data available', 
                     horizontalalignment='center', verticalalignment='center', 
                     transform=axes[1].transAxes)
    add_action_times(axes[1], action_time_data)
    format_time_axis(axes[1])
    axes[1].grid(True, linestyle='--', alpha=0.7)
    axes[1].legend()
    
    # Memory Requests Plot
    axes[2].set_title('Memory Requests')
    axes[2].set_xlabel('Time')
    axes[2].set_ylabel('Memory (MiB)')
    axes[2].plot(merged_data['timestamp'], merged_data[mem_requests_col], color='tab:green', marker='s', label='Memory Requests')
    add_action_times(axes[2], action_time_data)
    format_time_axis(axes[2])
    axes[2].grid(True, linestyle='--', alpha=0.7)
    axes[2].legend()
    
    # Memory Usage Plot
    axes[3].set_title('Memory Usage')
    axes[3].set_xlabel('Time')
    axes[3].set_ylabel('Memory (MiB)')
    if mem_usage_col in merged_data.columns:
        axes[3].plot(merged_data['timestamp'], merged_data[mem_usage_col], color='tab:red', marker='s', label='Memory Usage')
    else:
        axes[3].text(0.5, 0.5, 'No memory usage data available', 
                     horizontalalignment='center', verticalalignment='center', 
                     transform=axes[3].transAxes)
    add_action_times(axes[3], action_time_data)
    format_time_axis(axes[3])
    axes[3].grid(True, linestyle='--', alpha=0.7)
    axes[3].legend()
    
    plt.tight_layout()
    plt.subplots_adjust(top=0.88)
    
    # Save the resource dashboard figure
    plt.savefig(f'{output_dir}/{service}_resource_dashboard.png', dpi=150)
    plt.close()
    
    # --------------------- CPU Figure with Three Subplots in a Column (Top-Down Layout) ---------------------
    fig, axes = plt.subplots(3, 1, figsize=(10, 15))  # 3 rows, 1 column
    fig.suptitle(f'CPU Resources & Metrics for {service}', fontsize=16)
    
    # CPU Resources Plot (First subplot - top)
    axes[0].set_title('CPU Resources')
    axes[0].set_xlabel('Time')
    axes[0].set_ylabel('CPU Cores')
    axes[0].plot(merged_data['timestamp'], merged_data[cpu_requests_col], color='tab:blue', marker='o', label='CPU Requests')
    
    # Add CPU usage to the same plot if available
    if cpu_usage_col in merged_data.columns:
        axes[0].plot(merged_data['timestamp'], merged_data[cpu_usage_col], color='tab:orange', marker='x', label='CPU Usage')
    
    add_action_times(axes[0], action_time_data)
    format_time_axis(axes[0])
    axes[0].grid(True, linestyle='--', alpha=0.7)
    axes[0].legend()
    
    # Workload Metrics Plot (Second subplot - middle)
    axes[1].set_title('Workload Metrics (Requests/s from Locust)')
    axes[1].set_xlabel('Time')
    axes[1].set_ylabel('Requests/sec')
    
    if workload_metrics:
        for i, metric in enumerate(workload_metrics):
            # Skip plotting if all values are NaN
            if merged_data[metric].isna().all():
                continue
                
            line_style = ['-', '--', '-.', ':'][i % 4]  # Cycle through line styles
            marker_style = ['x', '+', '^', 'v'][i % 4]  # Cycle through markers
            metric_color = plt.cm.Set2(i % 8)  # Different color palette for workload
            
            # Create a more readable label - strip out the service name at the end
            label = metric.replace(f"_{service}", "").replace('_', ' ').title()
            
            axes[1].plot(merged_data['timestamp'], merged_data[metric], 
                       color=metric_color, linestyle=line_style, marker=marker_style, 
                       label=label)
    else:
        axes[1].text(0.5, 0.5, 'No workload metrics available', 
                     horizontalalignment='center', verticalalignment='center', 
                     transform=axes[1].transAxes)
    
    add_action_times(axes[1], action_time_data)
    format_time_axis(axes[1])
    axes[1].grid(True, linestyle='--', alpha=0.7)
    axes[1].legend()
    
    # Latency Metrics Plot (Third subplot - bottom)
    axes[2].set_title('Latency Metrics')
    axes[2].set_xlabel('Time')
    axes[2].set_ylabel('Latency (ms)')
    
    if latency_metrics:
        for i, metric in enumerate(latency_metrics):
            # Skip plotting if all values are NaN or metric doesn't exist
            if metric not in merged_data.columns or merged_data[metric].isna().all():
                continue
                
            line_style = ['-', '--', '-.', ':'][i % 4]  # Cycle through line styles
            marker_style = ['x', '+', '^', 'v'][i % 4]  # Cycle through markers
            metric_color = plt.cm.tab10(i % 10)  # Cycle through colors
            
            # Create a more readable label - strip out the service name at the end
            label = metric.replace(f"_{service}", "").replace('_', ' ').title()
            
            axes[2].plot(merged_data['timestamp'], merged_data[metric], 
                       color=metric_color, linestyle=line_style, marker=marker_style, 
                       label=label)
    else:
        axes[2].text(0.5, 0.5, 'No latency metrics available', 
                     horizontalalignment='center', verticalalignment='center', 
                     transform=axes[2].transAxes)
    
    add_action_times(axes[2], action_time_data)
    format_time_axis(axes[2])
    axes[2].grid(True, linestyle='--', alpha=0.7)
    axes[2].legend()
    
    plt.tight_layout()
    plt.subplots_adjust(top=0.95)
    
    # Save the CPU figure
    plt.savefig(f'{output_dir}/{service}_cpu_resources_top_down.png', dpi=150)
    plt.close()
    
    # --------------------- Memory Figure with Three Subplots in a Column (Top-Down Layout) ---------------------
    fig, axes = plt.subplots(3, 1, figsize=(10, 15))  # 3 rows, 1 column
    fig.suptitle(f'Memory Resources & Metrics for {service}', fontsize=16)
    
    # Memory Resources Plot (First subplot - top)
    axes[0].set_title('Memory Resources')
    axes[0].set_xlabel('Time')
    axes[0].set_ylabel('Memory (MiB)')
    axes[0].plot(merged_data['timestamp'], merged_data[mem_requests_col], color='tab:blue', marker='s', label='Memory Requests')
    
    # Add Memory usage to the same plot if available
    if mem_usage_col in merged_data.columns:
        axes[0].plot(merged_data['timestamp'], merged_data[mem_usage_col], color='tab:orange', marker='x', label='Memory Usage')
    
    add_action_times(axes[0], action_time_data)
    format_time_axis(axes[0])
    axes[0].grid(True, linestyle='--', alpha=0.7)
    axes[0].legend()
    
    # Workload Metrics Plot (Second subplot - middle)
    axes[1].set_title('Workload Metrics (Requests/s from Locust)')
    axes[1].set_xlabel('Time')
    axes[1].set_ylabel('Requests/sec')
    
    if workload_metrics:
        for i, metric in enumerate(workload_metrics):
            # Skip plotting if all values are NaN
            if merged_data[metric].isna().all():
                continue
                
            line_style = ['-', '--', '-.', ':'][i % 4]  # Cycle through line styles
            marker_style = ['x', '+', '^', 'v'][i % 4]  # Cycle through markers
            metric_color = plt.cm.Set2(i % 8)  # Different color palette for workload
            
            # Create a more readable label - strip out the service name at the end
            label = metric.replace(f"_{service}", "").replace('_', ' ').title()
            
            axes[1].plot(merged_data['timestamp'], merged_data[metric], 
                       color=metric_color, linestyle=line_style, marker=marker_style, 
                       label=label)
    else:
        axes[1].text(0.5, 0.5, 'No workload metrics available', 
                     horizontalalignment='center', verticalalignment='center', 
                     transform=axes[1].transAxes)
    
    add_action_times(axes[1], action_time_data)
    format_time_axis(axes[1])
    axes[1].grid(True, linestyle='--', alpha=0.7)
    axes[1].legend()
    
    # Latency Metrics Plot (Third subplot - bottom)
    axes[2].set_title('Latency Metrics')
    axes[2].set_xlabel('Time')
    axes[2].set_ylabel('Latency (ms)')
    
    if latency_metrics:
        for i, metric in enumerate(latency_metrics):
            # Skip plotting if all values are NaN or metric doesn't exist
            if metric not in merged_data.columns or merged_data[metric].isna().all():
                continue
                
            line_style = ['-', '--', '-.', ':'][i % 4]  # Cycle through line styles
            marker_style = ['x', '+', '^', 'v'][i % 4]  # Cycle through markers
            metric_color = plt.cm.tab10(i % 10)  # Cycle through colors
            
            # Create a more readable label - strip out the service name at the end
            label = metric.replace(f"_{service}", "").replace('_', ' ').title()
            
            axes[2].plot(merged_data['timestamp'], merged_data[metric], 
                       color=metric_color, linestyle=line_style, marker=marker_style, 
                       label=label)
    else:
        axes[2].text(0.5, 0.5, 'No latency metrics available', 
                     horizontalalignment='center', verticalalignment='center', 
                     transform=axes[2].transAxes)
    
    add_action_times(axes[2], action_time_data)
    format_time_axis(axes[2])
    axes[2].grid(True, linestyle='--', alpha=0.7)
    axes[2].legend()
    
    plt.tight_layout()
    plt.subplots_adjust(top=0.95)
    
    # Save the memory figure
    plt.savefig(f'{output_dir}/{service}_memory_resources_top_down.png', dpi=150)
    plt.close()

print(f"Created top-down CPU and memory visualizations for the specified services in the '{output_dir}' directory")
print(f"Also created 1x4 resource dashboard visualizations showing both requests and usage")

# Create a summary figure showing action durations
plt.figure(figsize=(10, 5))
plt.bar(action_time_data['iteration'], action_time_data['duration_seconds'])
plt.xlabel('Iteration')
plt.ylabel('Duration (seconds)')
plt.title('Action Duration by Iteration')
plt.xticks(action_time_data['iteration'])
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.tight_layout()
plt.savefig(f'{output_dir}/action_durations.png')
plt.close()

# Create a summary figure showing request rate over time from Locust
if not locust_workload_data.empty:
    plt.figure(figsize=(10, 5))
    plt.plot(locust_workload_data['datetime'], locust_workload_data['request_rate'], 
            color='tab:blue', marker='o', label='Request Rate')
    plt.xlabel('Time')
    plt.ylabel('Requests/sec')
    
    # Add action times if available
    add_action_times(plt.gca(), action_time_data)
    
    # Format time axis
    format_time_axis(plt.gca())
    
    # Add a title
    plt.title('Locust Workload Overview - Request Rate')
    
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/locust_request_rate.png', dpi=150)
    plt.close()
    
    print("Also created a summary of Locust request rates")

print("Also created a summary of action durations")