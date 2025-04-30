#!/bin/bash

# --- Configuration ---
# Set the desired traffic type here.
# Options should correspond to your Locust file naming convention,
# e.g., "diurnal" for "diurnal_traffic.py", "bursty" for "bursty_traffic.py".
TRAFFIC_TYPE="diurnal" # CHANGE THIS VALUE (e.g., "bursty", "constant")

# Load namespace from global config
CONFIG_FILE="src/conf/global_config.yaml"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Configuration file not found at ${CONFIG_FILE}"
    exit 1
fi

# Extract namespace from YAML file using grep and sed
# This assumes the format is 'namespace: value' in the YAML file
NAMESPACE=$(grep -E "^namespace:" "$CONFIG_FILE" | sed 's/^namespace:[[:space:]]*\(.*\)[[:space:]]*$/\1/')

if [ -z "$NAMESPACE" ]; then
    echo "Error: Could not extract namespace from ${CONFIG_FILE}"
    exit 1
fi

echo "Using namespace: ${NAMESPACE}"

# --- Derived Variables (Do not change unless structure changes) ---
TRAFFIC_FILE_BASENAME="${TRAFFIC_TYPE}_traffic.py"
TRAFFIC_FILE_PATH="traffic_rasing/${NAMESPACE}/${TRAFFIC_FILE_BASENAME}"
# Pattern for finding locust processes related to the specific traffic file
LOCUST_PGREP_PATTERN="locust.*${TRAFFIC_FILE_BASENAME}"
# Locust CSV output prefix
LOCUST_CSV_PREFIX="locust_results"
# ---

echo "--- Starting Experiment Setup ---"
echo "Using traffic type: ${TRAFFIC_TYPE}"
echo "Using traffic file: ${TRAFFIC_FILE_PATH}"

# Check if the specified traffic file exists
if [ ! -f "$TRAFFIC_FILE_PATH" ]; then
    echo "Error: Traffic file not found at ${TRAFFIC_FILE_PATH}"
    exit 1
fi

# Check for existing K8s monitoring processes and kill them
echo "Checking for existing K8s monitoring processes..."
if pgrep -f "python.*--namespace ${NAMESPACE}" > /dev/null; then
    echo "Found existing K8s monitoring processes. Terminating them..."
    pkill -f "python.*--namespace ${NAMESPACE}"
    sleep 2

    # Force kill if any processes are still running
    if pgrep -f "python.*--namespace ${NAMESPACE}" > /dev/null; then
        echo "Some K8s monitoring processes still running. Force terminating..."
        pkill -9 -f "python.*--namespace ${NAMESPACE}"
    fi
    echo "All existing K8s monitoring processes terminated."
else
    echo "No existing K8s monitoring processes found."
fi

# Check for existing Locust processes for the specified traffic type and kill them
echo "Checking for existing Locust processes (${TRAFFIC_TYPE})..."
if pgrep -f "$LOCUST_PGREP_PATTERN" > /dev/null; then
    echo "Found existing Locust processes (${TRAFFIC_TYPE}). Terminating them..."
    pkill -f "$LOCUST_PGREP_PATTERN"
    sleep 2

    # Force kill if any processes are still running
    if pgrep -f "$LOCUST_PGREP_PATTERN" > /dev/null; then
        echo "Some Locust processes (${TRAFFIC_TYPE}) still running. Force terminating..."
        pkill -9 -f "$LOCUST_PGREP_PATTERN"
    fi
    echo "All existing Locust processes (${TRAFFIC_TYPE}) terminated."
else
    echo "No existing Locust processes (${TRAFFIC_TYPE}) found."
fi

# Remove existing log files
echo "Removing previous log files..."
rm -f optimization_timing.csv
rm -f k8s_resources.csv
rm -f ${LOCUST_CSV_PREFIX}* # Remove specific locust results
rm -f k8s_monitor.log

# Create a log file for storing timing information
TIMING_LOG="optimization_timing.csv"
echo "Creating timing log: ${TIMING_LOG}"
echo "iteration,start_time,end_time,duration_seconds" > $TIMING_LOG

# Start Locust with the selected traffic file
echo "Starting Locust with ${TRAFFIC_FILE_BASENAME}..."
locust -f "${TRAFFIC_FILE_PATH}" --headless \
    --host http://192.168.49.2:30080 \
    --csv="${LOCUST_CSV_PREFIX}" > /dev/null 2>&1 &
LOCUST_PID=$!
echo "Locust started (PID: $LOCUST_PID). Waiting 60 seconds for ramp-up..."
sleep 60

# Start K8s resource monitoring in the background
echo "Starting K8s resource monitoring..."
python -m src.intent_exec.monitor --namespace ${NAMESPACE} --output k8s_resources.csv --interval 60 > k8s_monitor.log 2>&1 &
MONITOR_PID=$!
echo "K8s monitor started (PID: $MONITOR_PID)."

# Define a function to execute deployment and optimization process with timing
run_deployment() {
    local iteration=$1
    echo "===== Starting Optimization Iteration #${iteration} ====="

    # Record start time in both human-readable and epoch formats
    START_TIME=$(date "+%Y-%m-%d %H:%M:%S")
    START_EPOCH=$(date +%s)

    # Run the optimization
    echo "[${START_TIME}] Running optimization process..."
    python -m src.intent_exec.optimize
    OPTIMIZE_STATUS=$? # Capture exit status if needed

    # Record end time and calculate duration
    END_TIME=$(date "+%Y-%m-%d %H:%M:%S")
    END_EPOCH=$(date +%s)
    DURATION=$((END_EPOCH - START_EPOCH))

    # Log the timing information
    echo "${iteration},${START_TIME},${END_TIME},${DURATION}" >> $TIMING_LOG

    echo "===== Optimization Iteration #${iteration} completed ====="
    echo "       Started:  ${START_TIME}"
    echo "       Ended:    ${END_TIME}"
    echo "       Duration: ${DURATION} seconds"
    if [ $OPTIMIZE_STATUS -ne 0 ]; then
      echo "       WARNING: Optimization script exited with status ${OPTIMIZE_STATUS}"
    fi
    echo "" # Add a blank line for readability
}

# Run the deployments in sequence
NUM_ITERATIONS=36
echo "--- Starting ${NUM_ITERATIONS} Optimization Iterations ---"
for i in $(seq 1 ${NUM_ITERATIONS})
do
    run_deployment $i
done
echo "--- Completed ${NUM_ITERATIONS} Optimization Iterations ---"

# Stop Locust
echo "Stopping Locust (PID: $LOCUST_PID)"
if kill $LOCUST_PID > /dev/null 2>&1; then
    # Verify Locust termination
    sleep 2
    if ps -p $LOCUST_PID > /dev/null || pgrep -f "$LOCUST_PGREP_PATTERN" > /dev/null; then
        echo "Locust didn't terminate gracefully, forcing (pattern: $LOCUST_PGREP_PATTERN)..."
        pkill -9 -f "$LOCUST_PGREP_PATTERN"
    else
        echo "Locust successfully terminated."
    fi
else
    echo "Locust process (PID: $LOCUST_PID) already stopped or not found. Checking pattern..."
    if pgrep -f "$LOCUST_PGREP_PATTERN" > /dev/null; then
         echo "Locust process found via pattern. Forcing termination..."
         pkill -9 -f "$LOCUST_PGREP_PATTERN"
    else
         echo "No running Locust process found matching the pattern."
    fi
fi


# Stop the monitoring process
echo "Stopping K8s resource monitoring (PID: $MONITOR_PID)"
if kill $MONITOR_PID > /dev/null 2>&1; then
    echo "K8s monitor successfully signaled."
else
    echo "K8s monitor process (PID: $MONITOR_PID) already stopped or not found."
fi

echo "--- Experiment Finished ---"
echo "Timing information saved to ${TIMING_LOG}"
echo "K8s resource data saved to k8s_resources.csv"
echo "Locust results saved with prefix ${LOCUST_CSV_PREFIX}"
echo "K8s monitor logs saved to k8s_monitor.log"
echo "All tasks completed!"