import subprocess
import time
import yaml

def start_traffic():
    with open("src/conf/global_config.yaml", "r") as f:
        config = yaml.safe_load(f)

    traffic_file = config.get("traffic_file_path", "traffic_rasing/train-ticket/mix.py")
    print(f"Using traffic file: {traffic_file}")
    command = [
        "locust",
        "-f", traffic_file,
        "--headless",
        "-u", "20",
        "-r", "20",
        "--host", "http://192.168.58.2:32677",
        "--run-time", "1h",
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
    
    # Wait for 10 minutes (600 seconds) for the system to stabilize.
    # time.sleep(300)
    time.sleep(600)
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

def main():
    process = start_traffic()
    
    # Wait for the remainder of the run-time.
    # With the --run-time flag set to 2h, Locust will auto-stop after 2 hours.
    # Here, we wait 2 hours (7200 seconds) from the start.
    print("Traffic is running. Waiting for 2 hours...")
    time.sleep(7200)
    
    # Explicitly end the traffic, if still running.
    end_traffic(process)
    
    print("Test completed.")

if __name__ == "__main__":
    main()
