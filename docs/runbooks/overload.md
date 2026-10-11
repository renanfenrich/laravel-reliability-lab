# Overload and native FPM diagnostics

Scope: the dedicated local lab only. Preserve committed reports, retained telemetry and historical failures. Do not change SLI populations or reset counters to make a dashboard appear healthy.

## Identify the affected layer

Use the infrastructure dashboard's FPM active-child/queued-connection panels, per-pod CPU/throttling, PostgreSQL session/transaction panels, Redis depth and scheduler heartbeat age. Compare gateway/client latency against middleware latency: middleware omits waiting before Laravel and metric writes afterward. The load evidence's scheduled-arrival delay is a separate generator health signal.

Nine stable Prometheus targets include two independently scraped API FPM pools. A rolling update can temporarily expose more addresses until DNS discovery refreshes. Missing diagnostics are unknown, not zero utilization. Check current pods and /targets before declaring collection healthy. Native FPM counters reset when the pool restarts; rate per instance before summing. Shared PostgreSQL application counters have one authoritative scrape and must not be multiplied by API/worker replicas.

FPM status liveness and main-pool readiness serve different purposes. A saturated pod can fail readiness while native status continues to respond; no liveness restart is expected solely because the application pool is full. A main-pool deadlock can also leave native status healthy: readiness, queue growth, deadline misses and operator investigation remain necessary. Status is not proof of useful report progress.

Use only the repository kubeconfig/context:

```sh
.tools/kubectl --kubeconfig .kubeconfig --context kind-laravel-reliability-lab -n lab get pods
.tools/kubectl --kubeconfig .kubeconfig --context kind-laravel-reliability-lab -n lab get events --sort-by=.lastTimestamp
```

The fixed diagnostic routes live on internal port 8082; the public API port rejects /fpm-* and the tunnel exposes only authenticated Grafana. Do not add a host forward for diagnostics or publish FastCGI ports. Full request-level status is intentionally unavailable through these routes.

## Recover and verify

Stop only the project's current load generator using its recorded process/session, allowing bounded client timeouts and workers to drain. Keep API, worker, scheduler and database running. Capture failures, readiness changes, cohort deadlines and queued work before adjusting resources. Do not kill every worker or reset Redis to clear a queue; pending records and leases need the existing reconciliation path.

If a process actually exits, verify its restart count, container identity, native status and dependency readiness. Repeated healthy overload restarts indicate a probe regression. For growing backlog inspect worker retries, external latency/errors, scheduler heartbeat and PostgreSQL waits. Sparse wait samples cannot rule out transient contention. Do not add admission limits, children, CPU, indexes or extensions without a measured decision.

After recovery run make smoke and python3 scripts/observability-check.py. Retain every accepted report's deadline outcome; a late completion does not erase a miss. A lost successful acknowledgement is recovered with the original idempotency key, not a new submission identity. Compare duplicate-completion counters with committed records when relevant.

## Bounded reproduction

make g3-baseline runs one 60 requests/s, 180-second diagnostic baseline. make g3-load runs the G2 arrival protocol at 10/30/60 requests/s and a 600-second confirmation at an observed passing rate; it stops on saturation/generator limits. No higher rate is promised. make g3-probes intentionally suspends one API pod's four main children for 40 seconds, always resumes them, then kills that API master and verifies recovery. make g3-interruption terminates both correlated worker attempts under a separate 10 requests/s load cohort. Never overlap these experiments; they alter project availability and produce load/fault evidence outside the normal SLO population.

Before comparing runs record source/configuration, host activity, data size and warm-up conditions. Builds, development processes and repeated queries compete with the same workstation. A single passing rate or failing generator does not establish a precise capacity ceiling or any 30-day SLO result.
