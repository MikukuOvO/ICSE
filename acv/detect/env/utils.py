import json
import subprocess
import yaml

def list_deployments(namespace, config_yaml):
    try:
        result = subprocess.run(
            ["kubectl", "get", "deployments", "-n", namespace, "-o", "json"],
            capture_output=True,
            text=True,
            check=True,
        )
        deployments_data = json.loads(result.stdout)
        cluster_deployments = [item["metadata"]["name"] for item in deployments_data.get("items", [])]
    except Exception as e:
        print(f"Error fetching deployments in namespace {namespace}: {e}")
        cluster_deployments = []

    try:
        with open(config_yaml, 'r', encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
            deployments_cfg = config.get("deployments", {})
            if isinstance(deployments_cfg, dict):
                config_deployments = deployments_cfg.get(namespace, [])
            else:
                config_deployments = deployments_cfg
    except Exception as e:
        print(f"Error loading YAML config file {config_yaml}: {e}")
        config_deployments = []

    filtered_deployments = [dep for dep in cluster_deployments if dep in config_deployments]
    return filtered_deployments

if __name__ == '__main__':
    namespace = 'social-network'
    config_yaml = "config/deployments.yaml"
    deployments = list_deployments(namespace, config_yaml)
    print("Filtered deployments:")
    for dep in deployments:
        print(dep)
