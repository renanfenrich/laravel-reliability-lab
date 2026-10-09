# Laravel reliability lab — G1
A local portfolio lab for durable asynchronous reports, Kubernetes operations, observable outcomes and measured capacity. These experiments are **not production experience**. Short tests do **not** establish a rolling30-day SLO.

## Clean start (Linux/amd64)
Prerequisites: Docker access and Compose (observed29.9.0/5.6.0), kind0.30.0, Terraform1.16.5, Python3, curl, Git, Make; approximately32Gi RAM and >20Gi free disk. No host PHP/Composer required. Docker pulls/builds need network. Do not install privileged system packages through this repository. `make doctor` checks tools/resources/ports and refuses incompatible pinned kind/Terraform. Existing Kubernetes contexts are never selected. Local kubectl1.34.0 is downloaded and verified by cluster-up.

```sh
make doctor
make build
make cluster-up
make deploy
make verify
python3 scripts/experiments.py all
```

These commands initialize ignored `.env` with random local bearer/database/Redis credentials. Terraform stores secrets in ignored local state/tfvars; keep permissions and files private. Never commit/copy them into evidence. No remote repository or cloud credential is needed. build creates app/simulator images locally, cluster-up bootstraps only laravel-reliability-lab, and Terraform deploys all resource objects after bootstrap. deploy is repeatable, runs migrations, and rolls out code changes using source checksums. ConfigMap checksums trigger observability rollout on configuration changes. API readiness checks PostgreSQL and Redis; liveness only establishes process response. Worker/scheduler liveness checks process presence, not progress; scheduler heartbeat and processing SLI detect stalls.

Development only: `make build dev-up`, use API on `http://127.0.0.1:18080`, then `make dev-down`. Compose named volumes preserve data; tests use separate lab_test database, committed PostgreSQL migrations, never the lab database. Compose and Kubernetes stores are independent.

## Use the service
Use only synthetic subjects (`synthetic-example`). Read LAB_TOKEN from ignored .env into your local shell, without printing it. With the Kubernetes API loopback port-forward running:

```sh
.tools/kubectl --kubeconfig .kubeconfig --context kind-laravel-reliability-lab -n lab port-forward --address=127.0.0.1 service/api 18081:8080
```

In another shell:

```sh
set -a; source .env; set +a
curl -sS -H "Authorization: Bearer $LAB_TOKEN" -H 'Idempotency-Key: synthetic-demo-1' -H 'Content-Type: application/json' -d '{"subject":"synthetic-example"}' http://127.0.0.1:18081/api/reports
# Use the returned UUID:
curl -sS -H "Authorization: Bearer $LAB_TOKEN" http://127.0.0.1:18081/api/reports/UUID
```

POST returns202 only after committed acceptance; identical idempotent replay returns200/same ID, conflicting payload returns409. GET exposes pending/processing/completed/failed, attempts, result/error and overdue. Redis publication failure is recovered by scheduler. Attempts use DB leases/fencing; duplicate delivery cannot duplicate completed results. Terminal failures remain visible. X-Request-ID response matches JSON log correlation; supplied IDs are bounded/validated. No frontend.

Local fault controls: LAB_FAULTS=true, authenticated `X-Lab-Traffic: fault`, optional latency_ms0..4000/fail_attempts0..3. Defaults25ms/no failures. Fault controls are inputs to synthetic lab service, never a public administrative endpoint. Use `normal` for actual baseline/normal requests, `load` for rate experiments, `fault` for intentional disruption. Only normal participates in provisional SLO rules; experiment files retain every class separately. This is trusted local labeling, not a production anti-abuse policy.

## Observe and verify
Port-forward with the same explicit kubeconfig/context: service/grafana13000:3000, service/prometheus19090:9090, service/loki13100:3100. Grafana username `lab`, password local LAB_TOKEN. Provisioned dashboard: `/d/reliability-lab`. Prometheus `/targets` and `/alerts` expose metrics/alerts; no outbound notifications. Loki Explore: `{namespace="lab",app="worker"} | json`, then filter report_id/request_id as fields. Stop port-forwards with Ctrl-C.

`make test` runs meaningful application tests; `make rules` runs short/30-day simulated fixtures; `make smoke` verifies concurrent idempotent acceptance -> worker -> committed checksum. `make load-test` runs bounded increasing-rate load; `python3 scripts/experiments.py all` additionally runs baseline, external latency/failure, worker interruption and alert recovery. Full experiment takes several minutes and records raw samples. `make verify` repeats app/rules/Terraform/generated-manifest/smoke/observability checks, failing on the first failed command. Independent schema checks/hosted-CI definition are documented in validation. No hosted CI is implied.

## Stop/resume and reset
`make teardown` removes only dedicated Compose containers/network and named kind cluster. It preserves Compose volumes, .env, .runtime/postgres and archives Terraform state; observability emptyDir history is removed with cluster. Rebuild/recreate/deploy will reattach preserved PostgreSQL data; Redis loss is recovered from pending rows. This is not a validated backup mechanism. Persistent data on host is owned by PostgreSQL container UID; do not change it casually.

Destructive separate reset, **only after explicit human authorization**: stop lab with make teardown, then `CONFIRM=DELETE-LAB-DATA make data-reset`. It removes only this project's Compose volumes and mounted PostgreSQL directory contents. It has not been executed as part of G1. For resume read [status](docs/status.md), [checklist](docs/goals/G1.md) and current Git status before repeating discovery.

Architecture/decisions: docs/architecture.md, docs/decisions/. SLOs/budget: docs/slo.md and docs/error-budget-policy.md. Operator response: docs/runbooks/. Evidence, capacity and incident reports: docs/validation.md, docs/capacity.md, docs/incident.md, evidence/. Review boundary: READY FOR HUMAN REVIEW; renanfenrich owns Git flow, octavariumdigitalpartners mandatory reviewer; no push or merge under this goal.
