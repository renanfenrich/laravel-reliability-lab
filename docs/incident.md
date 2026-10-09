# Blameless local incident exercise — worker interruption
This is an executed local lab experiment, not a production incident. I intentionally sent SIGKILL to the worker process correlated with synthetic report `cabbb7df-14bd-45c0-a0d5-358eac3c9e43`. I preserved the committed acceptance and observed recovery instead of resetting data.

## Confirmed facts
The report was processing on attempt1 when I killed dedicated kind-node PID `150495` for container `a98f67382d8c1b68fb9ae205cb46cd7296157a5d260325b21f2e047e47d19f1a` in pod `worker-7697649bdb-2vl97`. The first worker could not finish. The scheduled reconciler logged worker.lease_expired, then the report processed on attempt2 and stored one completed checksum. Recovery from the experiment's observation start took 18.52s; no completion result was duplicated. This is below the60-second provisional deadline for this sample only. The fault report is excluded from normal-traffic SLOs.

- 2026-10-09T20:47:45.955570+00:00: report.processing (attempt 1)
- 2026-10-09T20:48:00.224015+00:00: worker.lease_expired
- 2026-10-09T20:48:00.268146+00:00: report.processing (attempt 2)

## Impact, cause and response
CONFIRMED impact: one synthetic report was temporarily unfinished; the durable record remained queryable. Cause was my planned process termination. I allowed the15-second fenced lease/reconciliation mechanism to recover the job and verified status/result plus correlated Loki logs. No person or dependency provider is blamed. HYPOTHESIS/UNKNOWN: this sample does not establish recovery probability under arbitrary process/database/node failures, real downstream side effects, multiple simultaneous interruptions or production delivery semantics.

An earlier pod-deletion injection did not interrupt the job (attempts remained1) and was INVALID for recovery proof; that failed evidence is retained. A subsequent scheduled log initially mixed JSON with console progress and failed correlation; routing task output to scheduler stderr fixed framing, and the final query returned lease-expiration/attempt2/completion events. No failures were hidden to obtain this result.

## Evidence and follow-up
Evidence: evidence/worker-final.json, worker-stderr-check.log, experiments-initial-partial.json, experiment-initial-error.json, worker-final-check.log and application/rule validation logs. Recorded HEAD was `c2236de1b58aee5faf64bf3173854ef2468507b7` with working-tree application checksum `540e6fe31c0707e06c049730ed40a0e3cb2f74419e60349adad89a3c4d763ba1`; the exact operating changes were subsequently committed as8dcfaca and are checked again after cluster recreation. No hosted CI result is claimed.

The operator runbook now uses explicit nested JSON extraction for correlation. Follow-up for later goals: test simultaneous interruption, persistent telemetry/backup recovery and a mutating downstream idempotency contract. Keep terminal failure visible and never reset missed-deadline evidence to make an alert recover.
