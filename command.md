minikube mount deployment/DeathStarBench/:/DeathStarBench
minikube addons enable metrics-server

locust -f traffic_rasing/social-network/mixed_traffic.py

ps -fp $(pgrep -f locust)

kubectl delete -f deployment/prometheus/
kubectl apply -f deployment/prometheus/

30m for chaos inject

minikube mount deployment/DeathStarBench/:/DeathStarBench & \
kubectl create namespace social-network
kubectl apply -f deployment/social-network-xirui/ && \
kubectl apply -f deployment/prometheus/ && \
kubectl apply -f deployment/otel-collector/


kubectl delete -f deployment/social-network-xirui/ && \
kubectl delete -f deployment/prometheus/ && \
kubectl delete -f deployment/otel-collector/ && \
kubectl delete namespace social-network 
