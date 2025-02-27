#!/usr/bin/env python3
import subprocess
import json
import math
import sys
import time
from datetime import datetime
import yaml

def extract_service_name(pod_name):
    """
    根据 Pod 名称提取 service 名称
    例如：my-service-5d9fc8f5cc-8h49m  ->  my-service
    规则：如果名称以 '-' 分隔后的段数>=3，则去掉最后两个段。
    """
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
    """
    返回一个字典：
      key: 从 Pod 名称提取出来的 service 名称（不含随机字符串）
      value: 对应的完整 Pod 名称（取第一个匹配到的）
    """
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
    """
    返回指定容器的资源限制（如果未指定，则返回第一个容器的限制）。
    """
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
    """
    解析 CPU 限制字符串（例如 "500m" 或 "1"），返回 stress-ng 所需的 CPU worker 数量（向上取整）。
    """
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
    """
    将内存限制字符串（例如 "512Mi", "1Gi"）转换为 stress-ng 可接受的格式（例如 "512M" 或 "1G"）。
    """
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
    # 读取配置信息
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading YAML config: {e}")
        sys.exit(1)

    chaos_cfg = config.get("chaos_injection", {})
    # 获取配置中的信息
    desired_namespace = chaos_cfg.get("namespace")
    desired_service = chaos_cfg.get("service")
    desired_container = chaos_cfg.get("container")
    desired_chaos_type = chaos_cfg.get("chaos_type", "CPU hog")  # default to CPU hog
    desired_duration = chaos_cfg.get("duration", "40m")         # default 40m

    # Step 1: 验证并使用 namespace
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

    # Step 2: 验证并使用 service -> pod
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

    # 获取 Pod JSON
    pod_data = get_pod_json(namespace, pod_name)
    if not pod_data:
        sys.exit(1)

    # 如果 Pod 中包含多个容器，且配置文件没有指定，则默认为第一个容器
    container_names = [c["name"] for c in pod_data["spec"]["containers"]]
    if desired_container:
        if desired_container not in container_names:
            print(f"Container '{desired_container}' not found in pod '{pod_name}'. Exiting.")
            sys.exit(1)
        container_name = desired_container
    else:
        # 如果仅有 1 个容器，则直接使用
        if len(container_names) == 1:
            container_name = container_names[0]
        else:
            print("Multiple containers exist but none specified in config. Exiting.")
            sys.exit(1)

    # 获取容器资源限制
    limits = get_container_resource_limits(pod_data, container_name)
    cpu_limit = limits.get("cpu")
    mem_limit = limits.get("memory")

    # Step 3: 根据 chaos_type 注入混沌
    if "cpu" in desired_chaos_type.lower():
        # CPU hog
        if cpu_limit is None:
            print("No CPU limit defined. Defaulting to 1 CPU worker.")
            num_workers = 1
        else:
            num_workers = parse_cpu_limit(cpu_limit)
        stress_cmd = f"stress-ng --cpu {num_workers} --timeout {desired_duration}"
        chaos_type = "CPU hog"
    elif "memory" in desired_chaos_type.lower():
        # Memory leak
        if mem_limit is None:
            print("No memory limit defined. Defaulting to 100M.")
            mem_for_stress = "100M"
        else:
            mem_for_stress = parse_memory_limit(mem_limit)
        stress_cmd = f"stress-ng --vm 1 --vm-bytes {mem_for_stress} --timeout {desired_duration}"
        chaos_type = "Memory leak"
    else:
        print(f"Invalid chaos type '{desired_chaos_type}' specified in config. Exiting.")
        sys.exit(1)

    # 构造 kubectl exec 命令
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
    
    injection_time = datetime.utcnow()

    print("Stress-ng has been started. Waiting for stability...")
    time.sleep(1200)  # adjust as needed
    print("The system is assumed to be stable.")

    # 保存相关信息到字典
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
    # If you want to pass a custom config path, e.g. python script.py /path/to/config.yaml
    if len(sys.argv) > 1:
        inject(sys.argv[1])
    else:
        inject()
