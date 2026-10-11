# Blameless incident exercise: blocked API request pool

This is a deliberately executed local fault exercise, not a production incident. Evidence: evidence/g3/probes-20261011T205849Z/result.json. The source/configuration belongs to G3's independent-probe phase; later histogram/load changes are separate evidence.

## Impact and confirmed observations

One of two API replicas had all four main FPM children suspended for approximately 40 seconds. Application readiness timed out and the pod became unready. The independent native FPM status listener and NGINX response remained available; neither container restarted during the suspension. The status summary showed queued connections, while suspended idle processes still appeared idle: active-child count alone cannot diagnose stopped workers. The other API replica remained available, but this experiment did not quantify user throughput during the suspension and does not prove zero user impact.

The test resumed every suspended child in finally. Dependency readiness returned HTTP 200. It then deliberately sent SIGKILL to the same pod's FPM master; its API container restart count increased from zero to one, readiness recovered, and observed recovery took 4.176 seconds. The HTTP sidecar did not restart. Public port 8080 rejected the diagnostic route with HTTP 404.

## Timeline (UTC)

- 2026-10-11T20:58:49Z: start recorded, target pod/container identities captured and the four main-pool children suspended.
- During the next 40 seconds: status liveness continued returning HTTP 200 in the sampled checks; main-pool readiness timed out and the pod was removed from serving endpoints. Exact samples and timing are in the JSON artifact.
- After suspension: children resumed, main-pool readiness returned and actual master termination/recovery was tested. Final timestamp and restart/container identities are in the artifact.

## Cause and response

The immediate cause was the intentional process suspension. G2's previous liveness route used the same request pool as API work, so a similar pool blockage could turn overload into a restart cascade. Moving process liveness to the independent native status listener changes that failure behavior without treating queue progress or dependency health as liveness.

The test confirmed the probe contract under this bounded fault. It does not prove that every real deadlock is detectable by status liveness: a working status pool can coexist with stuck main children. Readiness, queue depth, deadline misses and operator intervention remain necessary. Actual SIGKILL recovery demonstrates process-exit recovery, not recovery from every partial deadlock, database loss or node failure.

## Follow-up and prevention

The standalone Docker contract is in the CI definition; hosted G3 execution has not run because publication is unauthorized. Keep the readiness/liveness distinction, native queue gauges and source/configuration evidence. Avoid raising every probe timeout or disabling readiness to hide saturation. Follow docs/runbooks/overload.md for diagnosis and bounded reproduction. No report, counter or persistent data was reset during the exercise.
