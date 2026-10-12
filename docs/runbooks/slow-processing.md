# Slow or failed processing

Inspect ALL expired deadline cohorts, pending/processing/failed gauges, retries, leases, external errors/latency and worker restarts. A completed-only histogram cannot establish processing success. Fetch report status; preserve terminal error and result. Query Loki `{namespace="lab",app=~"worker|scheduler"} | json` then extract `report_id="context.report_id"` and filter report_id. Check Redis queue and scheduler heartbeat. Interrupted attempt should recover after 15-second lease expiry plus up to 5s reconciliation; retry_after is 20s. Terminal third failure remains failed.

A local dependency delay/failure may warrant ending the synthetic fault input; do not edit completed/failed rows. A worker restart is safe because claims are fenced and committed pending work is redispatched. Validate eventual recovery using smoke and a PostgreSQL row/correlated worker log. Late completion never restores its missed deadline. Capacity overload requires reducing offered rate or testing an authorized replica increase with new evidence, not inventing capacity. Observe Prometheus alert resolution and local Mailpit notifications and report actual elapsed time.

For native FPM/Redis/PostgreSQL diagnostic interpretation and overload drain, see [the overload runbook](overload.md).

For waiting-notification surplus, native pre-claim failures and owner-guard recovery, see [the queue runbook](queue-notifications.md).
