import subprocess
import time
import yaml
from ...utils.prometheus_url import get_minikube_ip

def kill_locust_processes():
    # First check if any locust processes exist
    check_command = "ps -ef | grep locust | grep -v grep"
    check_result = subprocess.run(check_command, shell=True, capture_output=True, text=True)
    
    if not check_result.stdout.strip():
        print("No locust processes found.")
        return
    
    # If processes exist, proceed with killing them
    kill_command = "ps -ef | grep locust | grep -v grep | awk '{print $2}' | xargs kill -9"
    result = subprocess.run(kill_command, shell=True)
    
    if result.returncode == 0:
        print("All locust processes have been terminated")
    else:
        print(f"Command failed with return code: {result.returncode}")

def start_traffic():
    # Kill all locust processes before starting a new one.
    kill_locust_processes()
    with open("acv/conf/global_config.yaml", "r") as f:
        config = yaml.safe_load(f)

    traffic_file = config.get("traffic_file_path", "traffic_rasing/social-network/mixed_traffic.py")
    print(f"Using traffic file: {traffic_file}")
    minikube_ip = get_minikube_ip()
    command = [
        "locust",
        "-f", traffic_file,
        "--headless",
        "-u", "100",
        "-r", "5",
        "--host", f"http://{minikube_ip}:30080"
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
    time.sleep(1*60)  # 35 minutes
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

