#!/bin/bash
# A simple setup script that lets the user choose which service to install.

# Display the menu options
echo "Please choose the service you want to set up:"
echo "1) Sock-shop"
echo "2) Social-network"
echo "3) Train-ticket"
echo

# Prompt for user input
read -p "Enter your choice (1-3): " choice

# Use a case statement to perform actions based on the user's selection
case "$choice" in
    1)
        echo "Setting up Sock-shop..."
        minikube start --cpus=16 --memory=516000MB -p sock-shop
        minikube addons enable metrics-server -p sock-shop
        kubectl config use-context sock-shop
        kubectl create namespace sock-shop
        kubectl apply -f deployment/sock-shop
        echo "Sock-shop has been set up successfully."
        ;;
    2)
        echo "Setting up Social-network..."

        minikube start --cpus=16 --memory=516000MB
        minikube addons enable metrics-server
        minikube mount /Data2/v-fenglinyu/microservice-bench/DeathStarBench:/DeathStarBench &
        kubectl config use-context social-network
        kubectl create namespace social-network
        kubectl apply -f deployment/social-network -n social-network

        echo "Social-network has been set up successfully."
        ;;
    3)
        echo "Setting up Train-ticket..."

        minikube start --cpus=16 --memory=516000MB -p train-ticket
        minikube addons enable metrics-server -p train-ticket
        kubectl config use-context train-ticket
        kubectl create namespace train-ticket 
        istioctl install --set profile=demo -y
        make deploy DeployArgs="--with-monitoring" Namespace=train-ticket
        kubectl label namespace train-ticket istio-injection=enabled
        kubectl rollout restart deployment -n train-ticket

        echo "Train-ticket has been set up successfully."
        ;;
    *)
        echo "Invalid choice. Please run the script again and select a valid option."
        exit 1
        ;;
esac

echo "Setup script completed."
