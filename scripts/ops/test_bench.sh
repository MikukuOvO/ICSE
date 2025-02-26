#!/usr/bin/env bash

# File: run_tasks.sh
# Usage: bash run_tasks.sh

CATALOGUE_FILE="src/curriculum_builder/task_bank/tasks_bench.json"
export PF_DISABLE_TRACING=true
echo "Disabling tracing for self-exploration script..."

# 如果 JSON 文件不存在就退出
if [[ ! -f "$CATALOGUE_FILE" ]]; then
  echo "JSON 文件 $CATALOGUE_FILE 不存在，请检查路径。"
  exit 1
fi
# 打印 task 数目
TASK_COUNT=$(jq '. | length' "$CATALOGUE_FILE")
echo "任务总数: $TASK_COUNT"

# 读取 JSON 的每个任务 (jq -c 会把每个对象按行输出)
while IFS= read -r TASK; do
  echo "Self-exploration script started..."
  echo "Running API script..."
  sh scripts/ops/api.sh
  # 提取 difficulty 和 description
  DIFFICULTY=$(echo "$TASK" | jq '.task_difficulty')
  DESCRIPTION=$(echo "$TASK" | jq -r '.task_description')

  echo "======================================"
  echo "Starting Task: $DESCRIPTION"
  echo "Difficulty: $DIFFICULTY"
  echo ""

  python -m src.intent_exec.test_bench \
    --intent "$DESCRIPTION" \
    --components "catalogue" \
    --namespace "sock-shop" \
    --cache_seed 42

  PYTHON_EXIT_CODE=$?
  echo "test_bench.py exited with code $PYTHON_EXIT_CODE"

done < <(jq -c '.[]' "$CATALOGUE_FILE")
