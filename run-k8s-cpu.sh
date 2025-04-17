#!/bin/bash

# Check for existing K8s monitoring processes and kill them
if pgrep -f "python.*--namespace social-network" > /dev/null; then
    echo "Found existing K8s monitoring processes. Terminating them..."
    pkill -f "python.*--namespace social-network"
    sleep 2
    
    # Force kill if any processes are still running
    if pgrep -f "python.*--namespace social-network" > /dev/null; then
        echo "Some K8s monitoring processes still running. Force terminating..."
        pkill -9 -f "python.*--namespace social-network"
    fi
    echo "All existing K8s monitoring processes terminated."
else
    echo "No existing K8s monitoring processes found."
fi

# Check for existing Locust processes and kill them
if pgrep -f "locust.*diurnal_traffic.py" > /dev/null; then
    echo "Found existing Locust processes. Terminating them..."
    pkill -f "locust.*diurnal_traffic.py"
    sleep 2
    
    # Force kill if any processes are still running
    if pgrep -f "locust.*diurnal_traffic.py" > /dev/null; then
        echo "Some Locust processes still running. Force terminating..."
        pkill -9 -f "locust.*diurnal_traffic.py"
    fi
    echo "All existing Locust processes terminated."
else
    echo "No existing Locust processes found."
fi

# Check for existing CPU controller processes and kill them
if pgrep -f "python.*k8s-cpu" > /dev/null; then
    echo "Found existing CPU controller processes. Terminating them..."
    pkill -f "python.*k8s-cpu"
    sleep 2
    
    # Force kill if any processes are still running
    if pgrep -f "python.*k8s-cpu" > /dev/null; then
        echo "Some CPU controller processes still running. Force terminating..."
        pkill -9 -f "python.*k8s-cpu"
    fi
    echo "All existing CPU controller processes terminated."
else
    echo "No existing CPU controller processes found."
fi

# Remove existing log files
rm -f optimization_timing.csv 
rm -f k8s_resources.csv
rm -f locust_results*
rm -f cpu_controller.log

# Define timing log file
TIMING_LOG="optimization_timing.csv"

# Record start time
START_TIME=$(date +%s)
echo "test_start_time,$(date +"%Y-%m-%d %H:%M:%S")" >> $TIMING_LOG

# Start K8s resource monitoring
echo "Starting K8s resource monitoring..."
python -m src.intent_exec.monitor --namespace social-network --output k8s_resources.csv --interval 60 > k8s_monitor.log 2>&1 &
MONITOR_PID=$!
echo "K8s resource monitoring started with PID: $MONITOR_PID"

# Record monitoring start time
echo "monitoring_start_time,$(date +"%Y-%m-%d %H:%M:%S")" >> $TIMING_LOG

# Start Locust for load testing
echo "Starting Locust load testing..."
locust -f traffic_rasing/social-network/diurnal_traffic.py --headless \
    --host http://192.168.49.2:30080 \
    --csv=locust_results > /dev/null 2>&1 &
LOCUST_PID=$!
echo "Locust started with PID: $LOCUST_PID"

# Record load test start time
echo "load_test_start_time,$(date +"%Y-%m-%d %H:%M:%S")" >> $TIMING_LOG

# Start the CPU controller
echo "Starting K8s CPU controller..."
python -m src.intent_exec.k8s-cpu > cpu_controller.log 2>&1 &
CPU_CONTROLLER_PID=$!
echo "K8s CPU controller started with PID: $CPU_CONTROLLER_PID"

# Record CPU controller start time
echo "cpu_controller_start_time,$(date +"%Y-%m-%d %H:%M:%S")" >> $TIMING_LOG

# Wait for the tests to complete (120 minutes = 7200 seconds)
echo "Running test for 120 minutes..."
sleep 7200

# Record test end time
echo "test_end_time,$(date +"%Y-%m-%d %H:%M:%S")" >> $TIMING_LOG

# Stop CPU controller
echo "Stopping CPU controller (PID: $CPU_CONTROLLER_PID)"
kill $CPU_CONTROLLER_PID

# Verify CPU controller termination
sleep 2
if ps -p $CPU_CONTROLLER_PID > /dev/null || pgrep -f "python.*k8s-cpu" > /dev/null; then
    echo "CPU controller didn't terminate gracefully, forcing..."
    pkill -9 -f "python.*k8s-cpu"
else
    echo "CPU controller successfully terminated."
fi

# Stop Locust
echo "Stopping Locust (PID: $LOCUST_PID)"
kill $LOCUST_PID

# Verify Locust termination
sleep 2
if ps -p $LOCUST_PID > /dev/null || pgrep -f "locust.*diurnal_traffic.py" > /dev/null; then
    echo "Locust didn't terminate gracefully, forcing..."
    pkill -9 -f "locust.*diurnal_traffic.py"
else
    echo "Locust successfully terminated."
fi

# Stop the monitoring process
echo "Stopping K8s resource monitoring (PID: $MONITOR_PID)"
kill $MONITOR_PID

# Verify monitoring termination
sleep 2
if ps -p $MONITOR_PID > /dev/null || pgrep -f "python.*--namespace social-network" > /dev/null; then
    echo "K8s monitoring didn't terminate gracefully, forcing..."
    pkill -9 -f "python.*--namespace social-network"
else
    echo "K8s monitoring successfully terminated."
fi

# Calculate total execution time
END_TIME=$(date +%s)
TOTAL_TIME=$((END_TIME - START_TIME))
echo "total_execution_time_seconds,$TOTAL_TIME" >> $TIMING_LOG

echo "All tasks completed!"
echo "Timing information saved to $TIMING_LOG"
echo "CPU controller log saved to cpu_controller.log"