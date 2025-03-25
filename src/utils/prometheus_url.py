import subprocess

def get_minikube_ip():
    # Run the command to get the IP address of the Minikube cluster.
    command = ["minikube", "ip", "-p", "v-xiruiliu"]
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    stdout, stderr = process.communicate()
    return stdout.strip()

def get_prometheus_url():
    prometheus_url = f"http://{get_minikube_ip()}:31090"
    return prometheus_url

if __name__ == "__main__":
    print(get_prometheus_url())