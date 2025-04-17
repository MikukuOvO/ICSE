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

# Remove existing log files
rm -f optimization_timing.csv 
rm -f k8s_resources.csv
rm -f locust_results*

# Create a log file for storing timing information
TIMING_LOG="optimization_timing.csv"
echo "iteration,start_time,end_time,duration_seconds" > $TIMING_LOG

locust -f traffic_rasing/social-network/diurnal_traffic.py --headless \
    --host http://192.168.49.2:30080 \
    --csv=locust_results > /dev/null 2>&1 &
LOCUST_PID=$!

sleep 60

# Start K8s resource monitoring in the background
python -m src.intent_exec.monitor --namespace social-network --output k8s_resources.csv --interval 60 > k8s_monitor.log 2>&1 &
MONITOR_PID=$!

# Define a function to execute deployment and optimization process with timing
run_deployment() {
  echo "===== Starting execution #$1 ====="
  
  # Record start time in both human-readable and epoch formats
  START_TIME=$(date "+%Y-%m-%d %H:%M:%S")
  START_EPOCH=$(date +%s)
  
  # Run the optimization
  python -m src.intent_exec.optimize
  
  # Record end time and calculate duration
  END_TIME=$(date "+%Y-%m-%d %H:%M:%S")
  END_EPOCH=$(date +%s)
  DURATION=$((END_EPOCH - START_EPOCH))
  
  # Log the timing information
  echo "$1,$START_TIME,$END_TIME,$DURATION" >> $TIMING_LOG
  
  echo "===== Execution #$1 completed ====="
  echo "       Started:  $START_TIME"
  echo "       Ended:    $END_TIME"
  echo "       Duration: $DURATION seconds"
}

# Run the deployments in sequence
for i in {1..12}
do
  run_deployment $i
done

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

echo "All tasks completed!"
echo "Timing information saved to $TIMING_LOG"