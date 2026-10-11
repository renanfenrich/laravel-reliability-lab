# G3 validation report

Status: **local acceptance complete; READY FOR HUMAN REVIEW**. No G3 push, PR, merge or release is authorized or executed. Hosted G3 CI is unexecuted; the workflow definition was updated and its relevant steps were checked locally. Earlier G2 hosted runs do not validate this branch.

## Passed

| Check | Actual result | Evidence |
| --- | --- | --- |
| Application reliability | 14 tests, 55 assertions; PostgreSQL/Redis; cumulative histogram boundaries and transaction rollback added | final-verify.log, application-tests.log |
| Native probe configuration and standalone contract | Restricted FPM/NGINX configuration valid; status/metrics remain available with all four main children suspended; public diagnostics rejected | fpm-config.log, nginx-config.log, runtime-contract.log, final-verify.log |
| Kubernetes probe fault | One main pool suspended for 40 seconds; readiness removed pod, no liveness restart; real master SIGKILL recovered in 4.18 seconds | probes-20261011T205849Z/result.json |
| Histogram microbenchmark | 500 observations, 5,000 to 500 SQL statements; identical series; one local timing sample each | metrics-benchmark-before/after/comparison.json |
| Rules | All 13 short and simulated long-window fixtures passed; no real monthly attainment inferred | final-verify.log |
| Terraform/manifests | fmt/validate, deterministic generation, 63/63 strict schema objects (zero skips), server dry-run | final-verify.log, schema-validation.log, server-dry-run.log |
| Journey | Eight concurrent idempotent requests produce one committed report/result; current smoke passed | smoke-final.json, final-verify.log |
| Metrics/logs/dashboard | Nine healthy targets, both native FPM pools; 61 dashboard queries; correlated worker logs, local mailbox authentication and rule health passed | observability-final.json |
| Sustained confirmation | 30 requests/s for 600 seconds, 18,000 accepted/on-time reports, zero errors, client p99 134.68 ms; both replicas | comparison-20261011T210320Z/result.json |
| Overload recovery | Failed 60 requests/s cohort retained; every accepted report eventually completed; API/HTTP/worker/DB restart counts unchanged; eleven resource histories nonempty | comparison-20261011T210320Z/ |
| Current-source worker interruption | Two correlated workers killed under separate 10 requests/s, 60-second load; both recovered on attempt two in 19.41/19.51 seconds; one stored result each and completed counter delta two | interruption-57134aaa30/ |
| Credential boundaries | Actual runtime credential/image-context scan and private identity exclusion passed; no credentials/backups committed | safety.log |

All evidence paths above are relative to evidence/g3/. Commands use the dedicated context; no unrelated service, cluster, permission or cloud resource was changed. G1/G2 folders and raw experiments remain preserved.

## Failed observations retained

- The after-change 60 requests/s, 180-second step failed latency and processing timeliness: p99 4.020 seconds, 74.71% within 500 ms, 6,430/10,800 deadlines met, zero HTTP errors. At the deadline snapshot 1,567 remained unfinished; all subsequently completed with 4,370 immutable misses. This is a saturation observation, not a passing load result.
- A standalone before-change 60 requests/s baseline passed; the after-change sequence failed. Different warm-up/data/background conditions prevent claiming a whole-service speedup or a stable 60 requests/s limit.
- The first isolated benchmark lacked tables. Its missing-table failure is preserved; migrations were run only in Compose lab_test before a successful retry.
- Baseline PostgreSQL JSON parsing failed on multiline output. Original error samples and a corrected supplemental collector remain; subsequent comparison samples use the repaired parser.
- An observability check ran during rollout and saw three DNS targets. The failed log remains; stabilized pre-load and final checks passed with two FPM pools/nine total targets.

## Unexecuted and limits

Hosted G3 CI/publication, higher rates, long-duration 60 requests/s confirmation, independent-host generation, an actual 30-day window, tracing, pg_stat_statements, a new index/admission policy, external SMTP, node/database disaster recovery and full external dashboard/disallowed-user audits are unexecuted. No dependency version, resource limit or main-child count was changed.

The confirmed bottleneck evidence combines CPU throttling, queued FPM connections and database/WAL pressure; sparse activity samples do not identify one dominant query. Redis notification surplus indicates repeated dispatch amplification, but raw per-message multiplicity is unverified. Report drain does not imply notification depth zero; stale queue work remained during confirmation. Data volume, host background activity and instrumentation differ between runs. Native status liveness does not prove main-pool/queue progress. Single-host storage/database/cluster and synthetic traffic limit interpretation. Read docs/g3/capacity.md and the overload runbook before repeating or extrapolating the experiment.
