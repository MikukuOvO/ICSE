import subprocess
import time
import yaml
from ...utils.prometheus_url import get_minikube_ip

def start_traffic():
    with open("src/conf/global_config.yaml", "r") as f:
        config = yaml.safe_load(f)

    traffic_file = config.get("traffic_file_path", "traffic_rasing/social-network/mixed_traffic.py")
    print(f"Using traffic file: {traffic_file}")
    minikube_ip = get_minikube_ip()
    command = [
        "locust",
        "-f", traffic_file,
        "--headless",
        "-u", "20",
        "-r", "20",
        "--host", f"http://{minikube_ip}:31090"
    ]
    
    # Redirect stdout and stderr to DEVNULL so no output is printed.
    process = subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True
    )
    print("Locust has been started. Waiting for stability...")
    
    # Wait for time about 35 minutes to let the system stabilize.
    time.sleep(2100)
    print("The system is assumed to be stable.")
    
    return process

def end_traffic(process):
    # Check if the process is still running.
    if process.poll() is None:
        print("Ending traffic...")
        process.terminate()  # Alternatively, process.kill() can be used.
        process.wait()
        print("Locust process terminated.")
    else:
        print("Locust process has already terminated.")

