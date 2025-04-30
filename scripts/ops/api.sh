#!/bin/bash

# Define color codes
RED='\033[1;31m'    # Bold Red for errors or critical inputs
GREEN='\033[1;32m'  # Bold Green for success messages
YELLOW='\033[1;33m' # Bold Yellow for warnings or ongoing actions
BLUE='\033[1;34m'   # Bold Blue for informational messages
NC='\033[0m'        # No color

# Update the GPT-4 API key
echo -e "${YELLOW}Updating GPT-4 API key...${NC}"
api_key=$(python acv/api/cloudgpt_aoai.py)

if [ -z "$api_key" ]; then
    echo -e "${RED}Error: Failed to fetch GPT-4 API key. Please check your Python script.${NC}"
    exit 1
fi

echo -e "${BLUE}Fetched API key:${NC} $api_key"
sed -i "s|api_key:.*|api_key: \"$api_key\"|" acv/api/secret.yaml

if [ $? -eq 0 ]; then
    echo -e "${GREEN}Successfully updated GPT-4 API key in secret.yaml.${NC}"
else
    echo -e "${RED}Failed to update GPT-4 API key in secret.yaml. Please check the file and permissions.${NC}"
    exit 1
fi

sed -i "s|api_key:.*|api_key: \"$api_key\"|" acv/api/secret_reasoning.yaml

if [ $? -eq 0 ]; then
    echo -e "${GREEN}Successfully updated GPT-4 API key in secret_reasoning.yaml.${NC}"
else
    echo -e "${RED}Failed to update GPT-4 API key in secret_reasoning.yaml. Please check the file and permissions.${NC}"
    exit 1
fi