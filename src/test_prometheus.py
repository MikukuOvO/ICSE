from intent_exec.agent.tool_functions_for_maintainer import query_prometheus

# PromQL query for P99 latency of compose-post-service
promQL = 'avg by (pod) (rate(container_cpu_usage_seconds_total{pod=~"ts-user-service.*"}[5m]))'
result = query_prometheus(promQL=promQL, duration='15m', step='1m')
print(result)