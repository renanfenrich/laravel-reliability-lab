# G1 validation report

Local goal complete; READY FOR HUMAN REVIEW. PASS means the stated check, not production reliability or monthly compliance. Final operating code commit 8dcfaca; later documentation/evidence commits do not change deployed application behavior.

| Check | Actual result | Evidence |
|---|---|---|
| Host tools/Docker/resources/ports/contexts | PASS; pinned kind 0.30.0/Terraform1.16.5/local kubectl 1.34.0; no default-context mutation | doctor.log, cluster-up.log |
| Pinned app/simulator builds | PASS; private infra/.env excluded from final image | build-final.log, build-scheduler-stderr.log, image-context-check.log, safety-verified.log |
| Application reliability tests | PASS 13 tests/47 assertions, PostgreSQL 18/Redis8.2; separate committed test DB | tests-scheduler-stderr.log, verify-recreation.log |
| Auth/validation/idempotency/durable queue-window/retries/duplicate/stale fencing/deadlines | PASS meaningful scenarios, subsecond deadline and content-length regression included | tests/Feature/ReportsTest.php and test logs |
| Rule mathematics/alerts | PASS 9 short +3 intended 30-day simulated fixtures; failures/latency/unfinished/missing/zero/recovery | rules-final.log, verify-recreation.log, observability/tests*.yml |
| Terraform init/fmt/validate | PASS; validation also with absent kubeconfig in isolated CI copy | terraform-final.log, ci-terraform-validation.log |
| CI Terraform image pin | PASS image executes1.16.5 | ci-terraform-image-version.log |
| Kubernetes schema/server validation | PASS 41/41 strict schema 1.34, no skips; server dry-run only | kubeconform-final.log, manifest-server-validation.log |
| Dedicated bootstrap/deploy/redeploy | PASS; Terraform owns deployment objects, kind cluster only | deploy-recreation.log, cluster-recreation.log |
| Full Kubernetes journey | PASS 8 concurrent idempotent submissions, one completed DB result | smoke.json, verify-recreation.log |
| Metrics/logs/Grafana | PASS exporter/KSM/cAdvisor targets, correlated exact report query,15 provisioned panels | observability.json, verify-recreation.log |
| Fault experiments/alert recovery | PASS healthy/external delay/exhaustion/SIGKILL and accelerated alert fired/resolved | experiments.json, worker-final.json |
| Capacity | Measured 40-rps passing burst/50-rps latency breach; all accepted deadline cohorts counted | capacity-retake.json, capacity-50.json, docs/capacity.md |
| Teardown/data retention/recreation | PASS 5221 prior records retained,5227 at after-check, old checksum survives | retention-before.json, retention-after.json, teardown.log |
| Actual credential values absent from Git candidates | PASS; ignored credential/state files remain private | secret-check.log, safety-verified.log |

## Failed/invalid observations retained

Initial PHP 8.4.13 DOM compilation, Closure middleware, missing Mockery/test env precedence, Terraform empty volumes/empty storageClass/restart annotations, PostgreSQL volume privileges, Alloy River syntax and promtool sample-limit/float comparisons failed before fixes. Corresponding evidence logs/diagnostic excerpts and Git history are retained; the first compiler output was truncated, so initial-build-failure.txt explicitly preserves only the observed excerpt. Some early command logs lack exact start/end wrapper timestamps; no durations were invented.

Initial pod deletion left attempts 1, INVALID for interruption proof. Second source run exposed second-resolution timestamps and client EOF framing. Pre-framing capacity and original60-rps/128-thread capacity were INVALID;512-thread60-rps retake still sender-limited (868ms lateness,7.33% client errors). Refined50-rps test sent accurately (1.28ms lateness) and breached latency with no HTTP errors; failures/timeouts remain raw. A scheduler JSON/console framing assertion failed before separate stderr routing; final exact-query log check passed. Pre-framing fault polling was tagged normal; that normal HTTP interval is unsuitable for compliance claims. No data reset or metric deletion was used to clear an alert.

## Unexecuted/unestablished

At the original local validation, hosted GitHub Actions had not run. Publication later started a hosted workflow; its final result is not established in this report. Other unestablished outcomes include actual rolling 30-day attainment, production experience/sizing/HA, cloud/AWS, sustained/load-balanced/multi-region tests, backups/full disaster recovery, external notification delivery, full browser/accessibility QA and destructive data-reset. These are explicit scope/measurement limits; not silently counted as passes. Pure simulator does not prove exactly-once mutating downstream effects. Server middleware metrics omit pre-middleware admission/bootstrap/client-network delay; client experiment timings expose this gap. Persistent PostgreSQL retention is not a backup proof; ephemeral telemetry history is lost on cluster deletion.

Command timestamps/durations/exit codes/SHA: evidence/commands.jsonl. Source/config/deployed-image versions: versions-current.json and composer.lock. Final reports: docs/incident.md and docs/capacity.md.

## Grafana panel regression repair

The user subsequently found panel errors. Original validation counted provisioned panels but did not exercise datasource plugins. Grafana startup auto-update removed registered Prometheus/Loki plugins and failed against read-only bundled files. Disable preinstallation and auto-update so exact image-bundled plugins remain loaded; read-only root stays enabled. `grafana-regression-before.log` records HTTP 404; `grafana-regression-after.log` and `observability.json` record both healthy datasources and15 successful panel queries with nonempty report-state, resource and log frames. Earlier observability evidence is preserved as `observability-before-grafana-fix.json`.

## Infrastructure and load rerun (2026-10-11)

Host collector unit conversion and Docker scope filtering tests passed. The new dashboard has 40 metric panels; all 55 queries across both dashboards returned frames. Five targets were UP. Smoke tests, 12 rule fixtures, Terraform fmt/validate, deterministic manifests, and credential checks passed. Prometheus configuration was validated with promtool inside the pod using its Kubernetes credentials. External check-config attempts failed because rule/service-account mounts were absent and did not establish configuration validity. An initial network-error query failed due to a label collision and was corrected. Evidence: `evidence/infrastructure-20261011` and `observability.json`. The browser showed current charts. Long-duration collector stability and overhead were not measured; hosted CI had not run at that time.

Separate load evidence: `evidence/load-20261011T175620Z`, with 2,640 requests. The highest passing tested rate was 40 requests/s; 50 requests/s showed latency saturation with client p99 of 13.97 s, zero HTTP errors, and 100% timely processing. This run preceded host collector installation; no retrospective host metrics are available.

## Alerts and local email (2026-10-11)

PASS: 13 promtool fixtures (ten short and three simulated 30-day windows), positive coverage of all 12 burn alerts, missing telemetry, zero traffic, recovery, and the new target-down condition. Pod-level amtool/promtool configuration checks passed. Terraform fmt/validate, deterministic generation of 46 manifest objects, and credential checks passed. New images are pinned to Alertmanager 0.34.1 and Mailpit 1.31.5. These results do not prove an observed 30-day SLO.

PASS in `evidence/email-5fdb4d90db`: 15 explicit notification-fixture injections exercised all firing/resolved routes. Three real Prometheus conditions fired and resolved: a terminal fault report, missing scheduler heartbeat, and stopped host collection. All 36 local emails were received and exported. SLO burn alerts were tested with mathematical and delivery fixtures, not live burn events. The scheduler and collector were restored; the terminal failed report was retained. Post-recovery smoke and observability checks passed: seven targets, healthy rules, active Alertmanager, inbox API 401 without credentials and 200 with credentials, and 55 Grafana queries. Command records identify the base SHA and working-tree changes; the final source commit is recorded in the evidence context.

Unexecuted at this experiment: external delivery, visual inbox browser validation (the in-app client blocked access), hosted CI, and inbox persistence/HA. Mailpit/Alertmanager emptyDir state is ephemeral; exported JSON provides durable evidence. The LAN inbox is http://192.168.1.9:18025 with `lab`/`LAB_TOKEN` authentication. The live experiment lasted six minutes and 26 seconds, separate from the SLO windows.
