#!/bin/bash

# Retrieve the current cluster name
cluster_name=$(kubectl config current-context)
if [ -z "$cluster_name" ]; then
    echo "Failed to retrieve the current cluster name. Please check your kubectl configuration."
    exit 1
fi

echo "Current cluster name is: $cluster_name"

# Assume the namespace is the same as the application name
namespace="$cluster_name"

# Set host URL to localhost since we are port-forwarding
case "$cluster_name" in
    "sock-shop")
        host_url="http://localhost:30080"
        ;;
    "social-network")
        host_url="http://localhost:8080"
        ;;
    "train-ticket")
        host_url="http://localhost:32677"
        ;;
    *)
        echo "Unsupported cluster name: $cluster_name"
        exit 1
        ;;
esac
echo "Selected host URL is: $host_url"

# Define the directory containing the Locust scripts based on the current cluster name
script_dir="traffic_rasing/${cluster_name}"

# Check if the directory exists
if [ ! -d "$script_dir" ]; then
    echo "Directory $script_dir does not exist. Please check the path."
    exit 1
fi

# List all .py files in the directory
py_files=("$script_dir"/*.py)
if [ ${#py_files[@]} -eq 0 ]; then
    echo "No .py files found in $script_dir."
    exit 1
fi

echo "The following Python files were found in $script_dir:"

# Prompt user to select a Locust script file
PS3="Please enter the number corresponding to the script you want to run (e.g., 1): "
select selected_file in "${py_files[@]}"; do
    if [ -n "$selected_file" ]; then
        echo "You have selected: $selected_file"
        break
    else
        echo "Invalid selection. Please try again."
    fi
done

# Execute the Locust command with the selected file and host URL
echo "Executing command: locust -f \"$selected_file\" --host=$host_url"
locust -f "$selected_file" --host=$host_url
