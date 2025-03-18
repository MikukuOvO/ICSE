import csv
import requests
import sys
import re
from datetime import datetime, timedelta
from os import mkdir
import os
import yaml
import pandas as pd
import matplotlib.pyplot as plt
import glob

# Load metrics from the YAML file instead of a text file
def get_metrics_map():
    # Use a default YAML file. Optionally, allow override via sys.argv[4].
    metrics_file = 'metrics_collection.yaml'
    if len(sys.argv) > 4:
        metrics_file = sys.argv[4]
    with open('src/conf/' + metrics_file, encoding="utf-8") as input_file:
        data = yaml.safe_load(input_file)
    # The YAML file is expected to have a top-level key 'social-network'
    return data.get('social-network', {})

# Validate a URL
def check_url(url):
    regex = re.compile(
        r'^(?:http|ftp)s?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return re.match(regex, url)

def merge_metrics(folder_path):
    """
    Merge all CSV files in folder_path (except merged.csv) into a single merged CSV.
    The merged CSV will have a header with the timestamp followed by the extracted service names.
    """
    def extract_name(filename):
        return os.path.splitext(os.path.basename(filename))[0]

    csv_files = [f for f in glob.glob(os.path.join(folder_path, "*.csv"))
                 if os.path.basename(f) != "merged.csv"]
    if not csv_files:
        print("No CSV files found in folder to merge.")
        return None

    merged_data = {}  # {timestamp: {filename: value, ...}}
    file_order = []
    file_names_mapping = {}

    for filename in csv_files:
        file_order.append(filename)
        file_names_mapping[filename] = extract_name(filename)
        with open(filename, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ts = row["timestamp"]
                value = row["value"]
                if ts not in merged_data:
                    merged_data[ts] = {}
                merged_data[ts][filename] = value

    def parse_ts(ts):
        return datetime.strptime(ts, "%d/%m/%Y %H:%M:%S")
    sorted_timestamps = sorted(merged_data.keys(), key=parse_ts)

    header = ["timestamp"] + [file_names_mapping[f] for f in file_order]

    merged_csv = os.path.join(folder_path, "merged.csv")
    with open(merged_csv, "w", newline="", encoding="utf-8") as out_file:
        writer = csv.writer(out_file)
        writer.writerow(header)
        for ts in sorted_timestamps:
            row = [ts]
            for filename in file_order:
                row.append(merged_data[ts].get(filename, ""))
            writer.writerow(row)

    print(f"Merging complete. Merged file created at {merged_csv}")
    return merged_csv

def plot_metrics(csv_file, output_dir):
    df = pd.read_csv(csv_file)
    
    df['timestamp'] = pd.to_datetime(df['timestamp'], format="%d/%m/%Y %H:%M:%S")
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    metric_columns = [col for col in df.columns if col != 'timestamp']
    
    for col in metric_columns:
        plt.figure(figsize=(10, 6))
        plt.plot(df['timestamp'], df[col], marker='o', linestyle='-')
        plt.title(col)
        plt.xlabel("Timestamp")
        plt.ylabel(col)
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        output_file = os.path.join(output_dir, f"{col}.png")
        plt.savefig(output_file)
        plt.close()

def export_metrics():
    # Fixed Prometheus URL
    prometheus_url = "http://192.168.49.2:31090"
    if check_url(prometheus_url) is None:
        print('Error: Invalid URL format')
        sys.exit(1)

    end_time = datetime.utcnow()
    start_time = end_time - timedelta(minutes=55)
    start_time_str = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
    end_time_str = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')

    print(f"Querying metrics from {start_time_str} to {end_time_str}")

    metrics_map = get_metrics_map()
    now = datetime.now
    ts_title = now().strftime('%Y-%m-%d-%H:%M:%S')
    new_folder = 'src/results/csv/metrics_' + ts_title
    mkdir(new_folder)

    # Go through each metric entry
    for metric_name, metric_info in metrics_map.items():
        # Each metric_info is expected to have { 'deploymentName': ..., 'promql': ... }
        if not isinstance(metric_info, dict):
            print(f"Skipping {metric_name} - format invalid (not a dictionary).")
            continue
        
        promql_query = metric_info.get("promql")
        if not promql_query:
            print(f"Skipping {metric_name} - no 'promql' specified.")
            continue

        print('Exporting metric: ' + metric_name)
        response = requests.get(
            f'{prometheus_url}/api/v1/query_range',
            params={
                'query': promql_query,
                'start': start_time_str,
                'end': end_time_str,
                'step': '30s'
            },
            verify=False
        )
        data = response.json()

        # We assume data['data']['result'] is a list of series
        results = data.get('data', {}).get('result', [])
        for result in results:
            # By default, we'll name the CSV by metric_name
            csv_file_name = f"{new_folder}/{metric_name}.csv"
            with open(csv_file_name, 'w', newline='', encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow(['timestamp', 'value'])
                for ts_value, metric_value in result['values']:
                    t = datetime.utcfromtimestamp(float(ts_value))
                    formatted_time = t.strftime("%d/%m/%Y %H:%M:%S")
                    writer.writerow([formatted_time, metric_value])

    # Merge all CSV files into merged.csv, then plot them
    merged_file = merge_metrics(new_folder)
    if merged_file:
        plot_path = os.path.join(new_folder, "plots")
        plot_metrics(merged_file, plot_path)

    return merged_file

def sum_up_metrics(merged_csv):
    """
    Reads the merged CSV and produces three figures:
      1) Average CPU usage (mCore)
      2) Average Memory usage (MiB)
      3) Average Latency (ms)
    Each figure is plotted as a single line vs. timestamp.
    
    Assumptions:
      - CPU columns end with '-cpu' (values in 'cores'). We convert to mCore by *1000.
      - Memory columns end with '-memory' (values in 'bytes'). We convert to MiB by / (1024*1024).
      - Latency columns end with '-latency' (values in ms). We leave as is (ms).
    """
    if not os.path.exists(merged_csv):
        print(f"{merged_csv} does not exist. Skipping sum-up.")
        return

    # Read data
    df = pd.read_csv(merged_csv)

    # Convert 'timestamp' to datetime, adjust format if needed
    df['timestamp'] = pd.to_datetime(df['timestamp'], format="%d/%m/%Y %H:%M:%S", errors='coerce')
    df = df.dropna(subset=['timestamp'])  # Drop rows where timestamp couldn't parse
    df = df.sort_values('timestamp')

    # Identify CPU, memory, and latency columns
    resource_cols = [c for c in df.columns if c != 'timestamp']
    cpu_cols = [col for col in resource_cols if col.endswith('-cpu')]
    mem_cols = [col for col in resource_cols if col.endswith('-memory')]
    lat_cols = [col for col in resource_cols if col.endswith('-latency')]

    # Convert these columns to numeric, ignoring non-numeric data
    for col in cpu_cols + mem_cols + lat_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Compute average CPU usage across all CPU columns, per row
    if cpu_cols:
        df['avg_cpu'] = df[cpu_cols].mean(axis=1)
    else:
        df['avg_cpu'] = 0.0

    # Convert CPU usage to milli-cores
    df['avg_cpu_mcore'] = df['avg_cpu'] * 1000

    # Compute average Memory usage across all Memory columns, per row
    if mem_cols:
        df['avg_mem'] = df[mem_cols].mean(axis=1)
    else:
        df['avg_mem'] = 0.0

    # Convert Memory usage from bytes to MiB
    df['avg_mem_mib'] = df['avg_mem'] / (1024 * 1024)

    # Compute average Latency across all Latency columns, per row (already in ms)
    if lat_cols:
        df['avg_latency'] = df[lat_cols].mean(axis=1)
    else:
        df['avg_latency'] = 0.0

    # Create a directory for plots (within the same folder as merged_csv)
    plot_dir = os.path.join(os.path.dirname(merged_csv), "plots")
    os.makedirs(plot_dir, exist_ok=True)

    # 1) Plot Average CPU usage in mCore
    plt.figure(figsize=(10, 6))
    plt.plot(df['timestamp'], df['avg_cpu_mcore'], marker='o', linestyle='-')
    plt.title("Average CPU Usage (All Services) in mCore")
    plt.xlabel("Timestamp")
    plt.ylabel("CPU Usage (mCore)")
    plt.xticks(rotation=45)
    plt.tight_layout()

    cpu_plot_path = os.path.join(plot_dir, "average_cpu_usage_mcore.png")
    plt.savefig(cpu_plot_path)
    plt.close()

    # 2) Plot Average Memory usage in MiB
    plt.figure(figsize=(10, 6))
    plt.plot(df['timestamp'], df['avg_mem_mib'], marker='o', linestyle='-')
    plt.title("Average Memory Usage (All Services) in MiB")
    plt.xlabel("Timestamp")
    plt.ylabel("Memory Usage (MiB)")
    plt.xticks(rotation=45)
    plt.tight_layout()

    mem_plot_path = os.path.join(plot_dir, "average_memory_usage_mib.png")
    plt.savefig(mem_plot_path)
    plt.close()

    # 3) Plot Average Latency (ms)
    plt.figure(figsize=(10, 6))
    plt.plot(df['timestamp'], df['avg_latency'], marker='o', linestyle='-')
    plt.title("Average Latency (All Services) in ms")
    plt.xlabel("Timestamp")
    plt.ylabel("Latency (ms)")
    plt.xticks(rotation=45)
    plt.tight_layout()

    lat_plot_path = os.path.join(plot_dir, "average_latency_ms.png")
    plt.savefig(lat_plot_path)
    plt.close()

    print("Plots created:")
    print(f"  CPU (mCore): {cpu_plot_path}")
    print(f"  Memory (MiB): {mem_plot_path}")
    print(f"  Latency (ms): {lat_plot_path}")


if __name__ == "__main__":
    csv_path = export_metrics()
    sum_up_metrics(csv_path)
