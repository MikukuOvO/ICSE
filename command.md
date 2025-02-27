minikube mount deployment/DeathStarBench/:/DeathStarBench
minikube addons enable metrics-server

python export_csv.py http://localhost:9090 2025-02-24T06:40:00Z 2025-02-24T06:53:00Z metrics.txt

locust -f traffic_rasing/social-network/mixed_traffic.py

ps -fp "$(pgrep -f locust)"

kubectl delete -f deployment/prometheus/
kubectl apply -f deployment/prometheus/

30m for chaos inject