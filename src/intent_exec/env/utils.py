import json
import subprocess
import yaml

def list_deployments(namespace, config_yaml):
    """
    返回指定 namespace 下，同时出现在 kubectl 获取的部署和 YAML 配置文件中的部署名称列表。
    参数：
      - namespace: Kubernetes 的命名空间
      - config_yaml: YAML 配置文件路径，文件中必须包含 'deployments' 键，对应部署名称列表
    """
    # 从 kubectl 获取当前 namespace 下所有 Deployment 的名称
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

    # 从 YAML 配置文件中加载配置的 Deployment 列表
    try:
        with open(config_yaml, 'r', encoding="utf-8") as f:
            config = yaml.safe_load(f)
            config_deployments = config.get("deployments", [])
    except Exception as e:
        print(f"Error loading YAML config file {config_yaml}: {e}")
        config_deployments = []

    # 过滤出同时存在于 cluster_deployments 和 config_deployments 中的名称
    filtered_deployments = [dep for dep in cluster_deployments if dep in config_deployments]
    return filtered_deployments

if __name__ == '__main__':
    namespace = 'social-network'
    config_yaml = "config/deployments.yaml"
    deployments = list_deployments(namespace, config_yaml)
    
    print("Filtered deployments:")
    for dep in deployments:
        print(dep)
