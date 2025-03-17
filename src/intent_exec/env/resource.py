#!/usr/bin/env python3
import subprocess
import json
import math
import sys
import time
from datetime import datetime, timezone
import yaml

def extract_service_name(pod_name):
    parts = pod_name.split('-')
    if len(parts) >= 3:
        return '-'.join(parts[:-2])
    else:
        return pod_name

def list_namespaces():
    try:
        result = subprocess.run(
            ["kubectl", "get", "ns", "-o", "json"],
            capture_output=True,
            text=True,
            check=True,
        )
        ns_data = json.loads(result.stdout)
        namespaces = [item["metadata"]["name"] for item in ns_data["items"]]
        return namespaces
    except Exception as e:
        print(f"Error fetching namespaces: {e}")
        return []

def list_pods(namespace):
    try:
        result = subprocess.run(
            ["kubectl", "get", "pods", "-n", namespace, "-o", "json"],
            capture_output=True,
            text=True,
            check=True,
        )
        pods_data = json.loads(result.stdout)
        service_to_pod = {}
        for item in pods_data["items"]:
            full_pod_name = item["metadata"]["name"]
            service_name = extract_service_name(full_pod_name)
            if service_name not in service_to_pod:
                service_to_pod[service_name] = full_pod_name
        return service_to_pod
    except Exception as e:
        print(f"Error fetching pods in namespace {namespace}: {e}")
        return {}

def get_pod_json(namespace, pod):
    try:
        result = subprocess.run(
            ["kubectl", "get", "pod", pod, "-n", namespace, "-o", "json"],
            capture_output=True,
            text=True,
            check=True,
        )
        pod_data = json.loads(result.stdout)
        return pod_data
    except Exception as e:
        print(f"Error fetching pod {pod}: {e}")
        return None

def get_container_resource_limits(pod_data, container_name=None):
    containers = pod_data["spec"]["containers"]
    if container_name:
        container = next((c for c in containers if c["name"] == container_name), None)
        if container is None:
            print(f"Container {container_name} not found in pod.")
            return {}
    else:
        container = containers[0]
        container_name = container["name"]
    resources = container.get("resources", {})
    limits = resources.get("limits", {})
    return limits

def parse_cpu_limit(cpu_str):
    try:
        if cpu_str.endswith("m"):
            millicores = float(cpu_str[:-1])
            cores = math.ceil(millicores / 1000)
            return cores
        else:
            cores = float(cpu_str)
            return math.ceil(cores)
    except Exception as e:
        print(f"Error parsing CPU limit '{cpu_str}': {e}")
        return 1

def parse_memory_limit(mem_str):
    try:
        if mem_str.endswith("Gi"):
            value = mem_str[:-2]
            return f"{value}G"
        elif mem_str.endswith("G"):
            return mem_str
        elif mem_str.endswith("Mi"):
            value = mem_str[:-2]
            return f"{value}M"
        elif mem_str.endswith("M"):
            return mem_str
        else:
            return mem_str
    except Exception as e:
        print(f"Error parsing memory limit '{mem_str}': {e}")
        return mem_str

def inject(config_path="src/conf/global_config.yaml"):
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading YAML config: {e}")
        sys.exit(1)

    chaos_cfg = config.get("chaos_injection", {})
    desired_namespace = chaos_cfg.get("namespace")
    desired_service = chaos_cfg.get("service")
    desired_container = chaos_cfg.get("container")
    desired_chaos_type = chaos_cfg.get("chaos_type", "CPU hog")  # e.g. "CPU hog", "Memory leak", "Latency"
    desired_duration = chaos_cfg.get("duration", "30m")

    namespaces = list_namespaces()
    if not namespaces:
        print("No namespaces found. Exiting.")
        sys.exit(1)

    if not desired_namespace:
        print("No namespace provided in config. Exiting.")
        sys.exit(1)

    if desired_namespace not in namespaces:
        print(f"Namespace '{desired_namespace}' not found. Exiting.")
        sys.exit(1)

    namespace = desired_namespace
    service_to_pod = list_pods(namespace)
    if not service_to_pod:
        print(f"No pods found in namespace '{namespace}'. Exiting.")
        sys.exit(1)

    if not desired_service:
        print("No service (derived from pod name) provided in config. Exiting.")
        sys.exit(1)

    if desired_service not in service_to_pod:
        print(f"Service '{desired_service}' not found in namespace '{namespace}'. Exiting.")
        sys.exit(1)

    pod_name = service_to_pod[desired_service]
    pod_data = get_pod_json(namespace, pod_name)
    if not pod_data:
        sys.exit(1)

    container_names = [c["name"] for c in pod_data["spec"]["containers"]]
    if desired_container:
        if desired_container not in container_names:
            print(f"Container '{desired_container}' not found in pod '{pod_name}'. Exiting.")
            sys.exit(1)
        container_name = desired_container
    else:
        if len(container_names) == 1:
            container_name = container_names[0]
        else:
            print("Multiple containers exist but none specified in config. Exiting.")
            sys.exit(1)

    limits = get_container_resource_limits(pod_data, container_name)
    cpu_limit = limits.get("cpu")
    mem_limit = limits.get("memory")
    chaos_type = None
    stress_cmd = None

    # ------------------------------------------
    # Existing chaos types
    # ------------------------------------------
    if "cpu" in desired_chaos_type.lower():
        if cpu_limit is None:
            print("No CPU limit defined. Defaulting to 1 CPU worker.")
            num_workers = 1
        else:
            num_workers = parse_cpu_limit(cpu_limit)
        stress_cmd = f"stress-ng --cpu {num_workers} --timeout {desired_duration}"
        chaos_type = "CPU hog"

    elif "memory" in desired_chaos_type.lower():
        if mem_limit is None:
            print("No memory limit defined. Defaulting to 100M.")
            mem_for_stress = "100M"
        else:
            mem_for_stress = parse_memory_limit(mem_limit)
        stress_cmd = f"stress-ng --vm 1 --vm-bytes {mem_for_stress} --timeout {desired_duration}"
        chaos_type = "Memory leak"

    elif "latency" in desired_chaos_type.lower():
        stress_cmd = f"tc qdisc add dev eth0 root netem delay 100ms"
        chaos_type = "Network latency (100ms)"

    else:
        print(f"Invalid or unknown chaos type '{desired_chaos_type}' specified in config. Exiting.")
        sys.exit(1)

    exec_cmd = ["kubectl", "exec", "-n", namespace, pod_name, "-c", container_name, "--"] + stress_cmd.split()
    print("\nExecuting the following command in the pod:")
    print(" ".join(exec_cmd))

    try:
        process = subprocess.Popen(exec_cmd)
        print("\nChaos command has been started in the background.")
        status = "launched"
    except Exception as e:
        print(f"\nError executing chaos command: {e}")
        status = "failed"
        sys.exit(1)

    injection_time = datetime.now(timezone.utc)
    print("Stress-ng has been started. Waiting for stability...")
    time.sleep(600)
    print("The system is assumed to be stable.")

    injection_info = {
        "injection_time": injection_time.isoformat(),
        "namespace": namespace,
        "service": desired_service,
        "pod": pod_name,
        "container": container_name,
        "resource_limits": limits,
        "chaos_type": chaos_type,
        "duration": desired_duration,
        "stress_command": stress_cmd,
        "kubectl_exec_command": " ".join(exec_cmd),
        "status": status
    }

    print("\nInjection Information:")
    print(json.dumps(injection_info, indent=4, ensure_ascii=False))

    return injection_info

if __name__ == "__main__":
    if len(sys.argv) > 1:
        inject(sys.argv[1])
    else:
        inject()
