#!/bin/bash

# 定义一个函数来执行部署和执行的过程
run_deployment() {
  echo "===== 开始第 $1 次执行 ====="
  
  echo "正在删除现有部署..."
  kubectl delete -f deployment/social-network-xirui/ && \
  kubectl delete -f deployment/prometheus/ && \
  kubectl delete -f deployment/otel-collector/ && \
  kubectl delete namespace social-network
  
  echo "正在创建新的部署..."
  minikube mount deployment/DeathStarBench/:/DeathStarBench & \
  MOUNT_PID=$!
  
  kubectl create namespace social-network
  kubectl apply -f deployment/social-network-xirui/ && \
  kubectl apply -f deployment/prometheus/ && \
  kubectl apply -f deployment/otel-collector/

  sleep 300
  
  echo "运行检测脚本..."
  python -m src.intent_exec.detect
  
  # 如果需要，可以在这里终止 minikube mount 进程
  # kill $MOUNT_PID
  
  echo "===== 第 $1 次执行完成 ====="
  echo ""
}

# 连续执行三次
for i in {1..3}
do
  run_deployment $i
done

echo "所有任务已完成！"