# G4 validation report

Status: local acceptance complete; READY FOR HUMAN REVIEW. G3 was approved/published/merged with exact-head hosted CI; G4 is local only and has no publication/merge/release authorization. Hosted G4 CI remains unexecuted; its definition automatically includes the real transport contracts.

## Passed

| Check | Actual result | Evidence under evidence/g4/ |
| --- | --- | --- |
| Application | 20 tests/96 assertions, PostgreSQL lab_test and isolated Redis database 15; cleanup only unique owned keys | application-tests.log, final-verify.log |
| Atomic transport/failure windows | Waiting deduplication, wrong-type error without orphan guard, isolated whole transport loss, stale owner, native pre-handle exhaustion and rollback | application-tests.log, queue protocol/ADR 013 |
| Before/after pause | Twenty reports, thirty-second worker pause: five waiting copies/report before, one after; all completed once, physical queue states drained, owned guards absent | pause-before/after-*/result.json, guard-cleanup.json |
| Real pre-claim process loss | Owned ephemeral PHP consumer SIGKILL after native reserve/before handle; SQL pending/attempts zero; recovered on business attempt one in 21.99 seconds, failure counter delta one, guard/queue cleared | preclaim-20261011T232706Z/result.json |
| Actual both-worker loss | Two active correlated workers killed under separate 10 requests/s cohort; completed on attempt two in 22.75/22.90 seconds, one stored result each, counter delta two; background load passed | interruption-*/result.json |
| Sustained confirmation | 30 requests/s for 600 seconds; 18,000 on-time, zero HTTP errors, p99 251.35 ms, 99.894% within 500 ms, processing p99 2.10 seconds; both replicas | comparison-20261011T232836Z/result.json |
| Rules/runtime/Terraform | All 13 short/simulated long-window fixtures, restricted native FPM contract, Terraform format/validate, deterministic manifests | final-verify.log |
| Schema/server validation | 63 strict objects, zero errors/skips; server dry-run | schema-validation.log, server-dry-run.log |
| Kubernetes smoke/dashboard/logs | Current eight-way idempotent smoke, nine healthy targets, 63 metric/log queries and correlated worker logs | smoke-final.json, observability-final.json |
| Compose development | Current images started without reset; accepted-to-completed synthetic journey passed on attempt one | dev-up.log, dev-smoke.json |
| Credential/identity boundaries | Actual runtime credential exclusion and private identity scan passed; no backups/credentials committed | safety.log |

G1/G2/G3 experiment folders remain preserved. Root smoke/observability outputs were copied into the G4 folder and restored to their prior committed versions after checks. Runtime versions/image IDs/source configuration and UTC events are retained. No schema/resource/dependency increase, admission policy, tracing stack, cloud resource or new public endpoint was introduced.

## Failed and corrected checks retained

The first counter test failed (19 tests/86 assertions) because Laravel after_commit discarded the publication return, misclassifying the first enqueue as suppression. Counters now use the actual Lua result; corrected suite passed. A pre-load observability process was prematurely recorded as passed but later failed stale-smoke Loki correlation. That claim was corrected explicitly; a fresh smoke/current correlated check passed during the 10 requests/s step. Failed logs remain. Raw logs retain original whitespace; style checks apply to source/documentation without rewriting diagnostic output.

## Failed load and missing telemetry retained

The nominal 60 requests/s step failed: 97 client failures (91 transport/timeouts/six HTTP502), p99 14.797 seconds, 10.56% within 500 ms, 1,932/10,794 committed reports timely (17.90%). Generator p99 delay 99.18 seconds invalidates a precise offered-rate/server ceiling. At deadline snapshot 2,638 were unfinished; all later completed with 8,862 misses retained. No restart cascade was observed.

Exporter up=0 appeared in 54 five-second samples during high-rate overload, approximately 23:36:57–23:41:22 UTC. Exporter-backed queue/business metric histories are incomplete; a separately recorded atomic Redis snapshot observed 3,069 waiting notifications when the incomplete gauge maximum was only 278. TelemetryUnavailable fired and collection recovered. Nonempty history is not continuous healthy telemetry or a monthly compliance proof. Source client/SQL cohort evidence remains distinct; no failure or missing interval was suppressed.

## Unexecuted and remaining risks

Hosted G4 CI/publication, live Redis flush, node/database disaster recovery, actual twenty-four-hour expiry soak, selective corruption repair, Redis Cluster/bulk/delayed deduplication, admission limits, resource/index changes, tracing, independent-host generation, higher-rate/longer high-rate tests, external SMTP and real thirty-day attainment are unexecuted. The guard is transport state, not exactly-once business processing; SQL fencing remains required. Sparse statistics cannot attribute one dominant bottleneck. Data growth, added physical drain, shared host and the tiny concurrent normal smoke limit before/after capacity attribution. See capacity.md, incident.md and queue-protocol.md.
