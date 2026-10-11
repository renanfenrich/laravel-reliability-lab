# G2 validation record

G2 remains active until all checklist items pass or blockers are explicitly recorded. G1 evidence is preserved. PASS refers to each stated local check, never production experience or a 30-day SLO.

| Check | Observed result | Evidence |
|---|---|---|
| Existing reliability suite under FPM image | PASS: 13 tests, 47 assertions against PostgreSQL/Redis | evidence/g2/runtime/g2-app-tests.log |
| Compose HTTP and dedicated NGINX/FPM gateway | PASS; both API pods served traffic; durable journey and replay | evidence/g2/runtime.json |
| Consistent logical snapshot and isolated restore | PASS: canonical report/metric/migration checksums and application readiness, twice | evidence/g2/backup-20a32f2e22 and backup-228f01a957 |
| Retained storage migration | PASS: six private exports, project-only host mount, 64 Terraform resources | evidence/g2/storage-export-cfb1dd3aba and storage/ |
| Full cluster recreation | PASS: old Prometheus up-vector, correlated completed log, inbox message and Grafana annotation survived | evidence/g2/persistence-cluster-recreation.json |
| Six telemetry pod replacements | PASS: new pod UIDs, all claims Bound, historical markers survived | evidence/g2/pod-recreation.json and persistence-pod-recreation.json |
| Final retained committed result | PASS: previously accepted completed result remains identical | evidence/g2/persistence-final-retention.json |
| Strict Kubernetes schema | PASS: 62 valid objects, zero errors/skips | executed kubeconform0.7.0 with Kubernetes1.34 schema |
| Promtool | PASS: 13 existing short/long-window simulated fixtures | local g2-rules.log |
| Simultaneous worker interruption | PASS: both processing attempt-one workers killed; both completed on attempt two with one result, completed counter delta2, background load passed | evidence/g2/interruption-c1b6f8086c/ |
| Sustained capacity and ten-minute confirmation | Unexecuted | pending |
| Hosted CI for G2 | Unexecuted; definition updated, no G2 push | .github/workflows/validate.yml |

## Failed attempts retained

NGINX default temporary paths failed on read-only root; configure every temp directory under /tmp. kind attempted unavailable platforms in a multi-platform image import; explicit amd64 imports passed. Shared mutable volume lists generated duplicate volumes; deep copy and uniqueness checks corrected the generator. A premature replica check queried the old deployment and lacked serving-pod headers; retested after rollout. Initial mailbox query was empty for an unknown reason; G1's exported emails remain intact, and a labeled notification fixture seeded G2 retention verification. A cold in-node registry pull exceeded the original rollout bound; preload declared pinned images through the host cache before rollout verification. Do not reinterpret these failures as passing checks.

## Boundaries

Same-host logical backup/retained telemetry is not off-host backup, PITR, HA, or arbitrary disaster recovery. Frozen filesystem migration copies are crash-consistent and verified with selected markers, not proof of completeness of every historical sample. Single-node Kubernetes, shared PostgreSQL metrics, short samples, host background activity, and local forwarding constrain capacity interpretation. External email, distributed tracing, cloud operations, actual 30-day outcomes, and G2 publication remain excluded/unexecuted.
