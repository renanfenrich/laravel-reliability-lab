# G4 validation ledger

Status: in progress; no publication authorized.

Passed: before-change 30-second worker pause directly observed five copies/report for 20 synthetic reports; all completed once on resume and notifications drained. Application suite 20 tests/95 assertions against isolated lab_test/Redis database 15; only uniquely owned queue/guard keys cleaned. Tests cover waiting deduplication, predictable enqueue error, whole isolated transport-state loss, stale owner, native pre-claim reservation exhaustion and SQL rollback.

Failed then corrected: dispatch counter fixture expected six suppressed attempts but observed seven because the initial after_commit enqueue returned null. Counters now use the actual Lua result. Initial failure and successful retry are retained in evidence/g4/.

Pending: live rollout, after-change pause, queue metrics/dashboard queries, comparable load/confirmation with physical notification drain, current-source both-worker interruption, complete verify/schema/safety and evidence reports. Hosted G4 CI is unexecuted because publication is unauthorized.
