# G1 resume state — READY FOR HUMAN REVIEW

Goal status: G1 complete and approved; release 0.1.0 published under explicit authorization. All phases A/B/C/D are complete. No PR, merge, or AWS/cloud resource was created. Hosted CI was in progress at the publication check; its final result is not established here. The documentation follow-up was reviewed and explicitly approved by the user for push and merge. renanfenrich owns Git flow; octavariumdigitalpartners is the mandatory reviewer/approver.

## Current resources

Repository /home/renanfenrich/Code/laravel-reliability-lab; documentation branch `docs/en-us-documentation` (approved for integration into `main`). The original `feat/g1-reliability-lab` branch is preserved. Dedicated kind cluster laravel-reliability-lab was torn down and recreated successfully; repository .kubeconfig points only to it. Original user kind-news context remains untouched. Terraform now manages 48 resources: namespace/Secret and 46 manifest objects (including local alert email). API 2, workers 2, singleton scheduler/exporter and full observability stack are running. PostgreSQL data is preserved under ignored .runtime/postgres; .env, tfvars and Terraform state remain ignored/private. Compose PG/Redis exist for tests (separate lab_test DB); dev API, worker, scheduler and simulator were subsequently started with make dev-up at the user’s request. Images g1 are local builds; actual source/config checksums and IDs are in versions-current.json.

## Passed checks and measurements

- Application: 13 tests/47 assertions against PostgreSQL/Redis; verification on code commit 8dcfaca after cluster recreation passed.
- Promtool: 10 short scenarios + 3 simulated 30-day scenarios; production-intended expressions, no claim of actual 30-day attainment.
- Terraform init/fmt/validate; strict Kubernetes 1.34 schema 41/41 resources (no skips); server dry-run; deterministic manifests; image/actual-credential exclusion checks.
- Kubernetes smoke:8 concurrent idempotent requests, 1 accepted report, completed checksum confirmed in PostgreSQL.
- Prometheus targets/resource metrics,15 provisioned Grafana panels and exact report-ID Loki query; accelerated fault alert fired/resolved.
- Effective worker SIGKILL: attempt 2 completed and scheduler lease-expiration JSON searchable. worker-final.json + incident.md preserve events.
- Capacity: valid20s bursts at 2/10/30/40 rps passed client 500ms/deadline60s thresholds.50-rps refinement: p99 client 11.50s, throughput 31.73rps,0 errors, all 1000 accepted reports timely, sender lateness 1.28ms; correlated API CPU throttling. This is one selected API pod, not whole-stack/production capacity.
- Teardown/recreate/verify: retained at least 5221 prior reports; count 5227 after subsequent checks and old completed attempt 2 checksum preserved. Observability history was intentionally lost; raw evidence exported first.

## Evidence, failed attempts and limits

See docs/validation.md, docs/evidence-method.md, docs/capacity.md and docs/incident.md; raw evidence/ includes timestamps/SHA/configs/samples/alerts/resource ranges and commands.jsonl. Earlier PHP extension, middleware/test-env, Terraform empty/default fields/restart annotations, Alloy syntax and promtool fixture failures were fixed and retained. Pod deletion did not prove worker interruption. Pre-framing client EOF latency and sender-limited60-rps probes are invalid for precise capacity attribution and remain visible. Scheduler stdout framing failed correlation before stderr fix. No failed observations were deleted to pass validation.

No current essential-tool blocker. Remaining limitations: CLI HTTP runtime; single-node DB/cluster; no backup/HA or sustained/load-balanced capacity; midpoint server metrics miss pre-middleware queueing/boot/network delay; missing HTTP metrics during DB outage invalidate compliance; telemetry emptyDir loses history; small synthetic samples and no 30-day observation. Local SMTP capture is validated; no external notification delivery or full browser/accessibility validation. Destructive data-reset implementation exists but was NOT executed. Human action: review local commits/artifacts; any push/publication/merge/later-cloud goal requires separate authorization.

## Resume commands

Read this file, docs/goals/G1.md and Git status; do not repeat discovery. Use make doctor, make verify for current stack. make dev-up starts independent dev API 18080; dedicated API/Grafana/Prometheus use documented loopback forwards. make teardown preserves PostgreSQL/Compose data. Never run data-reset without explicit authorization. Docker/kind/Terraform commands operate only on named lab resources. No work remains under G1 before human review.

## User-requested service access

All 14 Kubernetes deployments ready; Compose development stack running. Health checks returned HTTP 200 for Grafana, both APIs, Prometheus and Loki. Active session port-forwards: Grafana 192.168.1.9:13000; Kubernetes API 192.168.1.9:18081; Prometheus127.0.0.1:19090; Loki127.0.0.1:13100. Development API 127.0.0.1:18080. These forwards are temporary processes; recreate them using the documented explicit kubeconfig/context if stopped. PostgreSQL/Redis remain internal.

## Grafana datasource repair

User reported empty/error panels. Confirmed Grafana 13.2.3 background plugin updater unregistered Prometheus/Loki before failing to write bundled plugins on read-only root. Terraform now disables plugin preinstallation and automatic startup updates, retaining image-bundled versions. Only Grafana deployment changed. Expanded observability validation queries both datasource health endpoints and all 15 panels through Grafana, asserting data for report state, pod memory and logs. Regression failed before repair (HTTP 404), passed after repair. Previous checks proved direct backend metrics/logs and dashboard provisioning only, not functional Grafana queries; earlier completeness claim was too broad. LAN forward restarted after rollout; Grafana session database was ephemeral, requiring fresh login.

## LAN access / memory recovery (2026-10-10)

Connected Wi-Fi SSID NAXI_AP204_2G, workstation IPv4 192.168.1.9. Previous detached port-forward ended when Grafana was OOMKilled at 2026-10-10T01:05:21Z (exit137,512Mi limit). Increased only Grafana limit to1Gi through Terraform. Transient project-scoped systemd user unit laravel-reliability-lab-grafana-forward.service reconnects automatically (Restart=always,3s); make teardown stops it. No reboot enablement or unrelated service modification. Current health and panel query checks below; longer memory soak not executed, so recurrence is not ruled out. Previous capacity measurements precede this resource change.
Validation: HTTP 200 on LAN address, both datasource health and15 panel queries PASS; supervisor reconnected automatically after the Terraform rollout (NRestarts=1). Evidence: grafana-lan-recovery.json and observability.json.

## Load rerun and infrastructure dashboard (2026-10-11)

The load test was repeated from source `a6a19af`, preserving earlier evidence. New evidence: `evidence/load-20261011T175620Z`. Rates of 2, 10, 30, and 40 requests/s passed. At 50 requests/s, client p99 was 13.97 s, throughput was 29.25 requests/s, HTTP errors were zero, and all 1,000 reports completed on time. Sender delay was not limiting. The test stopped automatically at saturation; 60/120/240 requests/s were not executed. This run submitted 2,640 synthetic reports. No 30-day SLO attainment is claimed.

The Git-provisioned `/d/lab-infrastructure` dashboard has 40 metric panels and four sections. A native Linux/Docker collector connects through the kind bridge using the transient user unit `laravel-reliability-lab-host-metrics.service`. At installation, Prometheus had five healthy targets. All 55 metric/log queries across both dashboards returned frames. Collector tests cover unit conversion, exclusion of unrelated containers, and live collection. Terraform changed only Grafana/Prometheus configuration and deployments. Host scraping has no pre-installation history. Restarting Prometheus lost its emptyDir TSDB history; load samples were exported to JSON before rollout. Docker CLI I/O is rounded; host usage includes other processes; kind includes pods, so avoid double counting.

Validation: pod-level promtool configuration check passed. The first isolated attempt failed because Kubernetes files were absent from the validation container. A network-error query initially collided on labels; it was corrected and full verification passed. Records were preserved. These checks preceded publication. An idempotent collector restart briefly produced a scrape EOF; the next scrape and full check recovered. Evidence: `collector-restart-transient-failure.log` and `infrastructure-verify-final.log`.

## Alerts and local inbox (2026-10-11)

Review expanded positive coverage of all 12 SLO alerts and all three SLI families in simulated long windows; 13 promtool fixtures passed. Burn objectives and windows remain unchanged. `InfrastructureTelemetryUnavailable` detects an unavailable host/KSM/cAdvisor/Alertmanager/Mailpit target for one minute. All 15 rules route to Alertmanager 0.34.1; Mailpit 1.31.5 captures only `alerts@lab.test` with no external relay. Terraform added five resources and changed three without destroying data. amtool/promtool configuration checks, seven healthy targets, rule health, 55 Grafana queries, and smoke tests passed.

Run `evidence/email-5fdb4d90db`, 18:21:10–18:27:36 UTC: all 15 notification fixtures delivered firing/resolved messages. A fault report with exhausted retries plus temporary scheduler/collector outages triggered three real alerts: `LabDemoProcessingMiss`, `TelemetryUnavailable`, and `InfrastructureTelemetryUnavailable`, with firing/resolved emails. All 36 messages were exported. The scheduler was restored to one replica and the collector restarted; the failed report was retained. Normal SLO burn alerts were not triggered live. Their mathematics/windows use deterministic fixtures; delivery uses notification fixtures. No reset or silence was used to force resolution.

Authenticated inbox: http://192.168.1.9:18025, username `lab`, password `LAB_TOKEN`. The transient `laravel-reliability-lab-mail-forward.service` unit reconnects the forward. Recreate it with `LAB_BIND_ADDRESS=192.168.1.9 make mail-up`; stop it with `make mail-down`. SMTP/Alertmanager remain ClusterIP-only. Inbox API authentication checks passed (401/200). The in-app browser client blocked access, so visual inbox validation is unestablished. Mailpit/Alertmanager emptyDir state is lost on pod recreation; export messages. `make alert-test` repeats the approximately seven-minute experiment and temporarily pauses/restores the scheduler and host collector. See `docs/runbooks/alert-email.md`. No distributed tracing. CI includes amtool validation; hosted CI had not run at the time of this experiment.

## Authorized 0.1.0 publication (2026-10-11)

The user approved G1 and explicitly requested the public personal repository `renanfenrich/laravel-reliability-lab` and release 0.1.0. This authorization superseded the earlier publication restriction only for the initial release. No merge, remote infrastructure deployment, or cloud provisioning was authorized. Local audit: current credential values absent from 309 historical Git blobs; verify-safety passed. Initial `main` pointed to the approved release commit, preserving the local feature branch. Hosted CI had not run before publication.

Confirmed public repository: https://github.com/renanfenrich/laravel-reliability-lab, default branch `main`. Release https://github.com/renanfenrich/laravel-reliability-lab/releases/tag/v0.1.0 was published at 2026-10-11T18:33:17Z, without draft/prerelease status. The annotated tag points to `552a1b0a8d8ae29505c359c6b20bde677f0bbe2d`. The main/tag push succeeded; no merge occurred. The first hosted workflow https://github.com/renanfenrich/laravel-reliability-lab/actions/runs/38164292368 was in progress when checked; no passing result is established here. Public source access does not expose lab services or constitute a remote deployment.

## US English documentation review (2026-10-11)

The user requested US English throughout repository documentation. Work is on `docs/en-us-documentation`, based on published `main`. README, runbooks, release notes, status, validation, and capacity updates were translated; all tracked Markdown documents were reviewed. Historical raw evidence and runtime dashboard identifiers were preserved. No application or infrastructure behavior changed. The already-published GitHub release body is unchanged; this branch updates its repository source document. Language, link, and whitespace checks are recorded below. The user subsequently approved this follow-up and explicitly requested push and merge. This authorizes integration of these documentation changes only; no cloud deployment or infrastructure changes are authorized.

Documentation validation: PASS for all 26 tracked Markdown files: no remaining Portuguese prose or flagged non-US spellings, all three local Markdown links resolve, fenced shell/diagram blocks unchanged, and Git whitespace checks pass. Runtime credential exclusion also passed. Application tests were not rerun because only documentation changed. Historical evidence files were not modified.

## Documentation integration authorization (2026-10-11)
The user explicitly stated “Approved, push and merge” for the US English documentation changes. Integrate through a pull request under the personal account without inventing a separate octavariumdigitalpartners review. This direct authorization applies to this documentation change only; the normal reviewer requirement remains for subsequent work. GitHub publication/integration results are available in the linked pull request after execution.

## G2 active (2026-10-11)

User authorized definition and local execution of G2. Branch: feat/g2-capacity-recovery; base 71327a4. Scope/checklist: docs/goals/G2.md. Initial host: 31 GiB RAM, 20 GiB available, 84 GiB free disk; existing dedicated lab workloads ready. No implementation or experiment acceptance claimed yet. Next: pin NGINX stable runtime, preserve CLI worker commands, add gateway and verify both API replicas before sustained tests. No push/merge/publication authorized for G2. No tool blocker observed.
