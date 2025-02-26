from intent_exec.agent.tool_functions_for_maintainer import query_prometheus

# PromQL query for P99 latency of compose-post-service
promQL = "histogram_quantile(0.99,sum(rate(compose_post_latency_ms_bucket[5m])) by (le))"
result = query_prometheus(promQL=promQL, duration='5m')
print(result)