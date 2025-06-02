minikube start --kubernetes-version=latest --cpus=24 --memory=1048576MB

# Social Network

minikube mount deployment/DeathStarBench/:/DeathStarBench
minikube addons enable metrics-server

locust -f traffic_rasing/social-network/mixed_traffic.py

ps -fp $(pgrep -f locust)

kubectl delete -f deployment/prometheus/
kubectl apply -f deployment/prometheus/

30m for chaos inject

minikube mount deployment/DeathStarBench/:/DeathStarBench & \
kubectl create namespace social-network
kubectl apply -f deployment/social-network/ && \
kubectl apply -f deployment/prometheus/ && \
kubectl apply -f deployment/otel-collector/


kubectl delete -f deployment/social-network/ && \
kubectl delete -f deployment/prometheus/ && \
kubectl delete -f deployment/otel-collector/ && \
kubectl delete namespace social-network 
pkill -f "minikube mount deployment/DeathStarBench"

minikube addons enable metrics-server
cd autoscaler/vertical-pod-autoscaler
./hack/vpa-up.sh

kubectl exec -n social-network user-timeline-service-bb97d48c-s58p8 -c user-timeline-service -- tc qdisc del dev eth0 root