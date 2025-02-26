
export PF_DISABLE_TRACING=true
echo "Disabling tracing for self-exploration script..."

TASK_LIST_FILE="src/curriculum_builder/task_bank/task_list.json"

TASK_GENERATION_SCRIPT="scripts/ops/task.sh"

generate_task_list() {
  echo "Generating task list..."
  
  if [[ ! -x "$TASK_GENERATION_SCRIPT" ]]; then
    echo "Task generation script $TASK_GENERATION_SCRIPT not found or not executable."
    exit 1
  fi

  "$TASK_GENERATION_SCRIPT"
  
  if [[ $? -ne 0 ]]; then
    echo "Task generation script failed."
    exit 1
  fi
  
  echo "Task list generated successfully."
}

while true; do
  echo "======================================"
  echo "Starting a new iteration of task processing..."

  generate_task_list

  tasks=$(jq -c '.[]' "$TASK_LIST_FILE")

  if [[ -z "$tasks" ]]; then
    echo "No tasks found in $TASK_LIST_FILE. Generating a new task list."
    generate_task_list
    tasks=$(jq -c '.[]' "$TASK_LIST_FILE")
    if [[ -z "$tasks" ]]; then
      echo "Still no tasks found after regeneration. Exiting loop."
      exit 1
    fi
  fi

  task_count=$(echo "$tasks" | jq -s 'length')
  echo "Found $task_count tasks."

  echo "$tasks" | while IFS= read -r task; do
    echo "======================================"
    echo "Self-exploration script started..."

    echo "Running API script..."
    sh scripts/ops/api.sh
    if [[ $? -ne 0 ]]; then
      echo "API script failed to run. Skipping current task."
      continue
    fi

    echo "$task" > src/curriculum_builder/task_bank/tmp_task.json
    echo "Current task saved to tmp_task.json."

    description=$(jq -r '.task_description' src/curriculum_builder/task_bank/tmp_task.json)
    task_id=$(jq -r '.task_id' src/curriculum_builder/task_bank/tmp_task.json)
    echo "Fetched task id: $task_id"
    echo "Fetched task description: $description"

    echo "Calling python -m src.intent_exec.autorun with intent: $description"
    python -m src.intent_exec.autorun --intent "$description"

    echo "Adding the skill to the skill library..."
    python -m src.skill_library_builder.main

    echo "Tracking performance..."
    python -m src.performance_tracker.main --task_id "$task_id"

    echo "Task '$description' completed. Preparing to process the next task..."
    echo "======================================"

    sleep 5
  done

  echo "All tasks in the current task list have been processed."

  echo "Waiting before generating the next task list..."
  sleep 5

done

echo "All tasks have been processed."
