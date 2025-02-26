#!/bin/bash

# Exit immediately if any command returns a non-zero status
set -e

# Change into the target directory (update path as needed)
cd src/skill_library_builder/experience || {
  echo "Directory 'src/skill_library_builder/experience' not found."
  exit 1
}

# Remove all .jsonl files (including those in subdirectories)
find . -type f -name '*.md' -exec rm -f {} +

echo "All .md files (including in subfolders) have been removed."