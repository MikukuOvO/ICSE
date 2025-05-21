修改了若干处配置（包括 ip，端口，namespace，traffic file，服务名称等），用于在 train-ticket 上使用。
对 export_metrics 做了修改，添加了 injection_time，能够生成标注了 injection_time 的图。

Optimize 的实验目前集中于 ts-route-service, ts-order-service, ts-station-service 三个服务。（应该没有互相调用）
使用的 traffic file 为 traffic_rasing/train-ticket/changing.py，端口为 32677。

src/optimize_results_graph 中为 optimize 的实验结果。
如果需要修改一轮的运行时间，确保 traffic_rasing/train-ticket/changing.py, run-acv.sh, run-k8s-cpu.sh 中的时间对齐。

在 RCA 中，集中于 ts-route-service, ts-order-service, ts-travel-service 三个服务。（travel 会调用 route 和 order）
使用的 traffic file 为 traffic_rasing/train-ticket/mix.py，端口为 32677。
src/used_results 中为 RCA 的实验结果（带 0 的是在老版本下跑的，建议重新跑一次）。

对 src/intent_exec/agent/tool_functions_for_maintainer.py, src/conf/global_config.yaml, src/prompts/cluster_manager.yaml, src/prompts/service_manager_optimize.yaml 进行了一点修改，以测试将 raw data 从底层传给上层。