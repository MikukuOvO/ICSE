# Remove all subdirectories in src/results/AutoKube
cd src/results/AutoKube || {
  echo "Directory 'src/results/AutoKube' not found."
  exit 1
}

find . -mindepth 1 -type d -exec rm -rf {} +

echo "All subdirectories in 'src/results/AutoKube' have been removed."