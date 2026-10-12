# Local incident exercise: consumer lost before business claim

This is an executed synthetic local fault exercise, not a production incident. Evidence: evidence/g4/preclaim-20261011T232706Z/result.json; deployed application source 8dc1c37. It tests a different window from G3's interruption of already-processing attempts.

## Confirmed impact and recovery

With the project initially quiescent, two ordinary workers were paused and one authenticated synthetic fault report was durably accepted. An owned ephemeral PHP CLI consumer inside an API pod reserved its native Redis notification and then SIGKILLed itself before handle/SQL claim. The API master was not killed. Exit code 137 and the reserved job identity were recorded; SQL remained pending with zero business attempts, ready queue zero and reserved queue one.

The script restored the original two workers in finally. After the unchanged native twenty-second reservation expiry, the old delivery exceeded its single transport attempt before handle. The matching owner guard was released by the failed-job listener, its report-correlated event/counter became visible, and reconciliation published a new notification. The report completed on business attempt one, with observed recovery approximately 21.99 seconds after termination. Transport failure counter delta was one; its guard and ready/reserved/delayed state were absent at the end. No live queue key or database record was deleted.

## UTC timeline

- 2026-10-11T23:27:06Z: experiment started and quiescence checked; the dedicated workers were paused.
- The report was accepted, reserved by the ephemeral consumer and the consumer terminated. Exact output/report identity and exit status are retained in the JSON evidence.
- Two workers were restored and ordinary native reservation recovery resumed. Recovery took 21.986 seconds from the recorded termination observation; this is an observed local interval, not a universal recovery guarantee.
- 2026-10-11T23:27:32Z: final result saved after committed completion, matching guard cleanup and physical notification drain.

## Cause and prevention

The cause was intentional process termination between native reserve and business claim. A publication guard alone could strand pending acceptance if a native max-attempt rejection occurs before handle ever releases that guard. The failed-job listener performs owner-fenced cleanup so reconciliation can recover, while keeping native transport attempts separate from SQL business attempts.

Stale failed deliveries cannot clear a newer owner. SQL leases/result fencing remain necessary for interruption after claim; deduplication is not exactly-once delivery. A twenty-four-hour metadata expiry handles abandoned guards only as a safety bound and cannot guarantee a sixty-second SLO for selective corruption or very long outages. Whole isolated transport-state loss, wrong-type publication error and stale-owner races are separate real-Redis tests; no live Redis flush was performed.

Use docs/runbooks/queue-notifications.md and docs/g4/queue-protocol.md for diagnosis. The CI definition exercises the isolated transport contracts, but hosted G4 CI remains unexecuted because this goal does not authorize publication. Business terminal failures and immutable missed deadlines remain visible.
