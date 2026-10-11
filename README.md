# Laravel reliability lab

A local portfolio lab for durable asynchronous reports, Kubernetes operations, observable outcomes and measured capacity. These experiments are **not production experience**. Short tests do **not** establish a rolling 30-day SLO.

## Clean start (Linux/amd64)

Prerequisites: Docker access and Compose (observed 29.9.0/5.6.0), kind 0.30.0, Terraform 1.16.5, Python 3, curl, Git, Make; approximately 32Gi RAM and >20Gi free disk. No host PHP/Composer required. Docker pulls/builds need network. Do not install privileged system packages through this repository. `make doctor` checks tools/resources/ports and refuses incompatible pinned kind/Terraform. Existing Kubernetes contexts are never selected. Local kubectl 1.34.0 is downloaded and verified by cluster-up.

```sh
make doctor
make build
make cluster-up
make deploy
make verify
python3 scripts/experiments.py all
```

These commands initialize ignored `.env` with random local bearer/database/Redis credentials. Terraform stores secrets in ignored local state/tfvars; keep permissions and files private. Never commit/copy them into evidence. No remote repository or cloud credential is needed. build creates app/simulator images locally, cluster-up bootstraps only laravel-reliability-lab, and Terraform deploys all resource objects after bootstrap. deploy is repeatable, runs migrations, and rolls out code changes using source checksums. ConfigMap checksums trigger observability rollout on configuration changes. G2 uses NGINX/PHP-FPM for HTTP and an internal gateway to reach both API replicas. API readiness checks PostgreSQL and Redis through the application pool; G3 liveness/startup use an independent native FPM status pool. NGINX probes have their own response. Status liveness does not establish useful processing progress. Worker/scheduler liveness checks process presence, not progress; scheduler heartbeat and processing SLI detect stalls.

Development only: `make build dev-up`, use API on `http://127.0.0.1:18080`, then `make dev-down`. Compose named volumes preserve data; tests use separate lab_test database, committed PostgreSQL migrations, never the lab database. Compose and Kubernetes stores are independent.

## Use the service

Use only synthetic subjects (`synthetic-example`). Read LAB_TOKEN from ignored .env into your local shell, without printing it. With the Kubernetes API loopback port-forward running:

```sh
.tools/kubectl --kubeconfig .kubeconfig --context kind-laravel-reliability-lab -n lab port-forward --address=127.0.0.1 service/gateway 18081:8080
```

In another shell:

```sh
set -a; source .env; set +a
curl -sS -H "Authorization: Bearer $LAB_TOKEN" -H 'Idempotency-Key: synthetic-demo-1' -H 'Content-Type: application/json' -d '{"subject":"synthetic-example"}' http://127.0.0.1:18081/api/reports
# Use the returned UUID:
curl -sS -H "Authorization: Bearer $LAB_TOKEN" http://127.0.0.1:18081/api/reports/UUID
```

POST returns 202 only after committed acceptance; identical idempotent replay returns 200/same ID, conflicting payload returns 409. GET exposes pending/processing/completed/failed, attempts, result/error and overdue. Redis publication failure is recovered by scheduler. Attempts use DB leases/fencing; duplicate delivery cannot duplicate completed results. Terminal failures remain visible. X-Request-ID response matches JSON log correlation; supplied IDs are bounded/validated. No frontend.

Local fault controls: LAB_FAULTS=true, authenticated `X-Lab-Traffic: fault`, optional latency_ms0..4000/fail_attempts0..3. Defaults 25ms/no failures. Fault controls are inputs to synthetic lab service, never a public administrative endpoint. Use `normal` for actual baseline/normal requests, `load` for rate experiments, `fault` for intentional disruption. Only normal participates in provisional SLO rules; experiment files retain every class separately. This is trusted local labeling, not a production anti-abuse policy.

## Observe and verify

Port-forward with the same explicit kubeconfig/context: service/grafana13000:3000, service/prometheus19090:9090, service/loki13100:3100. Grafana username `lab`, password local LAB_TOKEN. Provisioned dashboard: `/d/reliability-lab`. Prometheus `/targets` and `/alerts` expose metrics/alerts; local-only email delivery is documented below. Loki Explore: `{namespace="lab",app="worker"} | json`, then use `| json report_id="context.report_id", request_id="context.request_id"` and filter those parsed fields. Stop port-forwards with Ctrl-C.

`make test` runs meaningful application tests; `make rules` runs short/30-day simulated fixtures; `make smoke` verifies concurrent idempotent acceptance -> worker -> committed checksum. `make load-test` runs bounded increasing-rate load; `python3 scripts/experiments.py all` additionally runs baseline, external latency/failure, worker interruption and alert recovery. Full experiment takes several minutes and records raw samples. `make verify` repeats app/rules/Terraform/generated-manifest/smoke/observability checks, failing on the first failed command. Independent schema checks/hosted-CI definition are documented in validation. No hosted CI is implied.

## Stop/resume and reset

`make teardown` removes only dedicated Compose containers/network and named kind cluster. It preserves Compose volumes, .env, .runtime/postgres and archives Terraform state; G2 retained observability data under .runtime/observability also survives cluster removal. Redis and temporary files remain ephemeral. Rebuild/recreate/deploy will reattach preserved PostgreSQL data; Redis loss is recovered from pending rows. This is not a validated backup mechanism. Persistent data on host is owned by PostgreSQL container UID; do not change it casually.

Destructive separate reset, **only after explicit human authorization**: stop lab with make teardown, then `CONFIRM=DELETE-LAB-DATA make data-reset`. It removes only this project's Compose volumes and mounted PostgreSQL directory contents. It has not been executed as part of G1. For resume read [status](docs/status.md), [checklist](docs/goals/G1.md) and current Git status before repeating discovery.

Architecture/decisions: docs/architecture.md, docs/decisions/. SLOs/budget: docs/slo.md and docs/error-budget-policy.md. Operator response: docs/runbooks/. Evidence, capacity and incident reports: docs/validation.md, docs/capacity.md, docs/incident.md, evidence/. Review boundary: READY FOR HUMAN REVIEW. renanfenrich owns Git flow and authorizes publication and merges; no separate reviewer account is required. Initial repository publication and release 0.1.0 were explicitly authorized; subsequent pushes, publication, and merges require authorization.

### LAN Grafana access that reconnects after a pod restart

On this Linux workstation, create a project-scoped transient user service (no root/install needed):
```bash
systemd-run --user --unit=laravel-reliability-lab-grafana-forward \
  --property=Restart=always --property=RestartSec=3 --property=StartLimitIntervalSec=0 \
  "$PWD/.tools/kubectl" --kubeconfig "$PWD/.kubeconfig" \
  --context kind-laravel-reliability-lab -n lab port-forward \
  --address=192.168.1.9 service/grafana 13000:3000
```
Use the workstation's current trusted LAN IP if different. Open http://192.168.1.9:13000/d/reliability-lab from the same LAN. Unit is transient, not enabled on reboot. Stop with `systemctl --user stop laravel-reliability-lab-grafana-forward.service`; `make teardown` also stops this unit. Status/logs: `systemctl --user status laravel-reliability-lab-grafana-forward.service` and `journalctl --user -u laravel-reliability-lab-grafana-forward.service`. Existing unit must be stopped/reset before repeating creation; do not create duplicate listeners. Grafana memory limit is 1Gi after an observed 512Mi OOM; this change does not establish long-term memory stability.

### Infrastructure dashboard

Open `/d/lab-infrastructure`. Its 40 metric panels cover CPU, memory, swap, load, repository filesystem space and inodes, physical disk I/O, physical network interfaces, Compose/kind containers, and pods in the `lab` namespace (requests/limits, throttling, readiness, restarts, OOM events, network, and filesystem usage). The original application dashboard remains at `/d/reliability-lab`.

`make deploy` starts the native host collector using the Python standard library and the installed Docker CLI, discovers the kind bridge gateway, and provisions scraping through Terraform. Linux with a user systemd session and Docker access is required. No privileged package installation is needed. `make host-metrics-up` and `make host-metrics-down` control only `laravel-reliability-lab-host-metrics.service`. Recreate the transient service after reboot; `make teardown` stops it. Port 19100 binds only to the internal gateway. No Docker socket is mounted in pods. If the gateway changes, run `make deploy` to regenerate the Prometheus hostAlias.

Host metrics cover the entire workstation, including other processes. The kind Docker container already includes pods; do not add those measurements together. Docker CLI I/O values are rounded and useful for trends rather than precise disk/network benchmarks. Docker memory excludes inactive cache and differs from the cAdvisor working set. No host history exists before collector installation. The final panels show collection health and scrape age. Unavailable metrics remain unknown rather than being converted to zero.

### Alerts and local email inbox

Prometheus → Alertmanager 0.34.1 → Mailpit 1.31.5 → `alerts@lab.test`. The inbox captures email locally with no external relay or forwarding. SMTP port 1025 and Alertmanager port 9093 remain internal to the cluster. The UI/API use Basic authentication with username `lab` and the local `LAB_TOKEN` as the password.

`make mail-up` exposes the inbox at `127.0.0.1:18025`. On a trusted LAN, run `LAB_BIND_ADDRESS=192.168.1.9 make mail-up`, then open http://192.168.1.9:18025. `make mail-down` closes access; teardown also stops the transient service. G2 retains inbox and Alertmanager state in project-local PVCs across pod and dedicated cluster recreation. Retained local disk is not a backup or HA; tests still export messages and evidence. Use synthetic data only.

`make rules` tests the rules. `make alert-test` tests firing and resolved notifications for all 15 alerts using explicit notification fixtures, followed by three real Prometheus scenarios. It temporarily pauses this lab's scheduler and host collector, records alerts, restores services in `finally`, and waits for the five-minute fault cohort to leave the window. Allow approximately seven minutes. Do not run it during other tests or terminate it with SIGKILL. Synthetic failures use `traffic=fault` and do not affect the normal SLO population. Notification fixtures use `mode=notification-fixture-ID` and do not prove actual SLO burn rates. See [the email alert runbook](docs/runbooks/alert-email.md).

## Goals and G2 execution

[G1](docs/goals/G1.md) is complete and published as 0.1.0. [G2](docs/goals/G2.md) completed local capacity and recovery validation and is published in [PR #2](https://github.com/renanfenrich/laravel-reliability-lab/pull/2), merged under explicit owner authorization. [G3](docs/goals/G3.md) implements overload resilience and bottleneck attribution locally under explicit authorization; publication requires separate owner authorization. See [current status](docs/status.md).

The G2 runtime uses NGINX 1.30.5 and PHP 8.4.26 FPM. `make dev-up` exposes the Compose HTTP container on loopback port 18080. Kubernetes API/exporter pods use nonroot HTTP sidecars; the gateway Service exercises both API replicas. Port-forward `service/gateway 18081:8080` for application access. The `X-Lab-API-Pod` response header supports experiment distribution checks. Client measurements include admission/network/metric-write overhead omitted by the original middleware SLI.

`make g2-runtime` validates distribution and the asynchronous journey. `make g2-backup` creates a private consistent logical dump, restores it only into a new isolated database, compares canonical fingerprints, and checks application readiness. `make g2-load` runs bounded three-minute rate steps and a ten-minute passing-rate confirmation. `make g2-interruption` kills both correlated worker processes during a separate load cohort and verifies leased-attempt recovery. See [load methodology](docs/g2/load-method.md) and [backup recovery](docs/g2/backup-recovery.md). Do not run experiments concurrently with other fault/capacity tests.

G2 bootstrap mounts ignored `.runtime/observability` into only the named kind node. Six Retain PVCs preserve Prometheus, Loki, Grafana, Alertmanager, Mailpit, and Alloy data. Deploy imports pinned Linux/amd64 images through the host Docker cache and refuses nodes without the project bind mount. Clean checkout needs network once for pinned images; pulls/imports complete before rollout verification. Static PV sizes are not quotas; monitor free disk. Prometheus uses time and size retention, without claiming an actual 30-day history. `make teardown` preserves PostgreSQL, telemetry, and Compose volumes. No telemetry reset is performed by the separate database reset command. See [the storage runbook](docs/g2/storage-runbook.md) for the one-time G1 migration and retention checks.

G2 measured results: [capacity](docs/g2/capacity.md), [recovery](docs/g2/recovery-report.md), and [validation](docs/g2/validation.md). The ten-minute 30 requests/s confirmation passed; the failed 60 requests/s step and generator limits remain documented. No rolling 30-day outcome is claimed.

## G3 overload resilience and diagnostics

G3 keeps the same pinned versions, four main FPM children and resource limits. Independent status liveness survives a blocked main pool; readiness still removes an unavailable application pod. A headless, internal diagnostics Service lets Prometheus scrape both native FPM pools without duplicating shared application counters. Six additional infrastructure dashboard panels cover FPM occupancy/queued connections, PostgreSQL activity/statistics, Redis queue depth and scheduler heartbeat. No diagnostic port is published to the host or Cloudflare.

Durable histograms now increment their cumulative buckets/count/sum in one atomic SQL statement. The isolated fixture reduced 5,000 statements to 500 while preserving every value and transaction rollback. This is measured statement overhead, not an inferred production capacity gain. No extra CPU/children, admission limit or schema change was introduced.

Use make g3-runtime for the standalone restricted Docker probe contract; make verify includes it. make g3-baseline runs a single diagnostic 60 requests/s step; make g3-load runs 180-second steps at 10/30/60 requests/s and a 600-second passing-rate confirmation. make g3-probes intentionally suspends one main pool for 40 seconds and verifies actual API process-failure recovery. make g3-interruption repeats both worker terminations under a separate bounded load cohort. Never run these generators/fault tests together. Commands retain sanitized evidence in evidence/g3/ and preserve data. See [the overload runbook](docs/runbooks/overload.md), [G3 checklist](docs/goals/G3.md), and [validation ledger](docs/g3/validation.md). [Measured results](docs/g3/capacity.md): 30 requests/s for ten minutes passed; 60 requests/s failed latency/timeliness with zero HTTP errors and no restart cascade. Every accepted report eventually completed; misses remain visible. Local G3 acceptance is complete, without publication or hosted G3 CI.
