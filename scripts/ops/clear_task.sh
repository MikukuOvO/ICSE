#!/bin/bash

# Exit immediately if any command returns a non-zero status
set -e

# Change into the target directory (update path as needed)
cd src/curriculum_builder/task_bank || {
  echo "Directory 'src/curriculum_builder/task_bank' not found."
  exit 1
}

# Remove all .jsonl files (including those in subdirectories)
rm task_list.json
rm task_log.json

echo "All .json files have been removed."