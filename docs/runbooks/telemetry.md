# Telemetry unavailable

Treat SLO state as UNKNOWN. Check Prometheus targets, exporter readiness, scheduler heartbeat, DB, Alloy and Loki/Grafana health. `TelemetryUnavailable` aggregates missing/down exporter, missing heartbeat and scheduler staleness >30s for 1m. Search app logs for telemetry.write_failed. Metrics share PostgreSQL so database outage is a shared failure domain; exporter up alone is not proof of complete request capture.

Restore only dedicated lab resources, then verify a new accepted/completed report increments metrics and its request/report IDs are searchable in Loki. Check kubelet and kube-state-metrics targets separately; missing resource metrics impair bottleneck analysis. Preserve the missing interval in validation/incident reports. Do not interpolate success, remove samples or claim 30-day results from recovered partial history. Local Grafana uses lab user and ignored LAB_TOKEN as password; never save password/screenshots containing secrets to Git.
