# G2 local recovery exercises

These are executed synthetic lab exercises, not production incidents or recovery guarantees. G1 raw evidence is preserved.

## Logical PostgreSQL restore

Two repeatable-read snapshots were dumped and restored into new isolated databases. Canonical checksums/counts for reports, metric samples, and migrations matched exactly; application readiness against the restored database passed. The live database was never overwritten. First snapshot: 7,872 reports, 552,092-byte custom dump, 0.332-second backup and 0.624-second measured restore/check interval. Pre-recreation snapshot: 7,876 reports, 552,777 bytes, 0.332-second backup and 0.644-second restore/check interval. See `evidence/g2/backup-20a32f2e22/result.json` and `backup-228f01a957/result.json` for precise values and SHA.

The interval includes restore, fingerprint comparison, example result lookup, and readiness; it is not a contractual RTO. Snapshot time determines this exercise's recovery point. Dumps are private (0700 directory/0600 files), ignored, and retained. Same PostgreSQL instance/local disk restoration does not prove off-host recovery, PITR, role recovery, or arbitrary disk-loss survival.

## Observability retention

Six components were exported privately while briefly process-frozen, resumed, and migrated to retained host-backed PVCs. The dedicated kind cluster was recreated with a project-only host mount. After recreation, the same historical Prometheus up-vector, completed-report worker log, inbox message, and Grafana annotation were verified. Six observability pods were then replaced; their UIDs changed and those markers still survived. All six telemetry PVCs were Bound. The previously committed report result remained identical. This proves selected marker retention, not completeness of every historical event.

Migration failures remain visible: a cold image pull exceeded the initial rollout bound, and a pre-migration inbox query was empty for an unknown reason. Host-cache amd64 imports make cold starts explicit before rollout checks. G1's exported 36 messages remain durable evidence; a clearly labeled notification fixture supplied the G2 inbox marker. No file/state deletion was used to pass recovery. Frozen filesystem exports are crash-consistent, not application-consistent/off-host backups. Retained local disk is not HA.

## Simultaneous worker interruption under load

At 2026-10-11T19:06:27Z, I killed both worker processes correlated to separate synthetic reports in processing attempt one. I rechecked both active states immediately before one dedicated-node kill command. Kubernetes restarted the workers and the reconciler recovered their expired leases. Both reports completed on attempt two with one stored result each. Observed post-kill recovery was 22.57 and 22.70 seconds. The fault completed counter increased exactly twice, providing a second check against duplicate completion.

A concurrent, separately classified 10 requests/s, 60-second load cohort sent 600 reports: zero HTTP errors, client p99 64.46 ms, and all accepted reports completed within their deadlines. Every accepted deadline expired before timeliness was calculated. Fault reports remain outside normal SLO traffic. Evidence: `evidence/g2/interruption-c1b6f8086c/`, including pre-kill logs, exact container/PID correlation, results, and raw background samples. The full exercise ran from 19:06:26Z to 19:08:29Z.

No arbitrary process/node/database failure probability, exactly-once external mutating effect, or 30-day SLO is established. Retained local PostgreSQL, an available reconciler, at-least-once Redis delivery, and bounded/fenced attempts were required for this observed recovery. Terminal failures and historical missed deadlines were preserved.
