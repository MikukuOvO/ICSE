from intent_exec.agent.tool_functions_for_maintainer import query_prometheus

promQL = 'histogram_quantile(0.99,sum(rate(read_home_timeline_latency_ms_bucket[5m])) by (le))'

result = query_prometheus(promQL=promQL, duration='20m', step='30s')
print(result)