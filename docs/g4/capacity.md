# G4 local queue and capacity measurement

Status: local comparison and confirmation completed; the failed high-rate/generator-limited step is retained. The goal is waiting-notification deduplication and recoverability, not a promised higher capacity or monthly SLO result.

## Controlled mechanism comparison

The before/after experiment paused only this project's two workers for approximately thirty seconds, accepted twenty synthetic fault reports and inspected at most five hundred waiting payloads in memory. Exported artifacts contain only multiplicity counts/report IDs and aggregate queue states, never raw payloads. The scripts restored the original replica count in finally.

| Case | Source | UTC interval | Maximum waiting copies/report | Final business attempts | Final ready/reserved/delayed |
| --- | --- | --- | ---: | --- | --- |
| Before guard | 32ebeb0 harness; deployed G3 application | 2026-10-11 23:16:33–23:17:15 | 5 | 1 each | 0/0/0 |
| After guard | 8dc1c37 application | 2026-10-11 23:25:24–23:26:08 | 1 | 1 each | 0/0/0 |

All forty reports completed with one stored result each across the two cases. A separate read-only check found zero remaining owned guards after the after-change pause. This directly confirms the five-second redispatch amplification mechanism and its suppression within the tested guard window; it does not establish indefinite exactly-once transport. Guards expire after twenty-four hours and selective state corruption remains outside the whole-state-loss recovery guarantee.

The actual pre-claim interruption recovered after about 21.99 seconds: an ephemeral consumer reserved one report then SIGKILLed itself before handle. SQL stayed pending/zero attempts; native transport exhaustion and owner cleanup allowed completion on business attempt one. Counter delta one and physical/guard cleanup were checked. A separate current-source interruption of both already-processing workers also passed: each report completed on business attempt two in approximately 22.75/22.90 seconds, one result each and completed counter delta two.

## Load method

Source 0fb2942 reuses the G2/G3 256-thread scheduled-arrival generator, fifteen-second client timeout, unique idempotency keys, serving-pod response identity and fully expired accepted cohorts. Steps are 10/30/60 requests/s for 180 seconds, followed by 600 seconds at an observed passing rate. Stop on latency/error/timeliness saturation or generator limitation; no rate is a promised target. Unlike G3, confirmation requires both accepted business records and ready/reserved/delayed notification depth to drain to zero first.

Versions, main FPM child count, CPU/memory requests/limits, simulator defaults, probes and database schema were unchanged. Internal gateway/API Service is the load path, not Cloudflare. All load samples remain separate from normal/fault SLO traffic. Higher rates and real thirty-day outcomes are unexecuted.

The 10 requests/s step passed, with zero errors, all accepted reports timely and client p99 66.26 ms. The 30 requests/s step passed with zero errors, all timely and p99 170.50 ms. The 60 requests/s step failed: 97 client failures (91 transport/timeouts, six HTTP 502), p99 14.797 seconds, only 10.56% within 500 ms, and 1,932/10,794 committed deadlines met (17.90%). Client p99 arrival lateness was 99.18 seconds; the nominal 180-second offered schedule took 290.04 seconds to finish client responses. This generator-limited result cannot establish a precise 60 requests/s server ceiling. There were 10,703 successful acknowledgements but 10,794 committed records; retain both populations. At the deadline snapshot 2,638 reports remained unfinished, with 8,862 misses. Later completion cannot repair them.

The experiment started the 30 requests/s, 600-second confirmation at 2026-10-11T23:43:34Z only after accepted records and all three physical notification states drained. It passed: 18,000 accepted/completed/on-time reports, zero HTTP errors, client p99 251.35 ms, 99.894% within 500 ms, processing p99 2.10 seconds, generator p99 delay 1.11 ms, both APIs used (9,125/8,875). This failure is worse than the earlier G3 sequence on some measures; no whole-service capacity gain is claimed from the deduplication improvement.

## Attribution limits

G3's earlier queue surplus was inferred from non-atomic aggregate gauges; G4's pause counted actual payload membership for twenty known IDs. The load dashboard still samples non-atomic business counts versus atomic queue-state reads, so do not interpret every instantaneous difference as duplicate delivery. Native reservations are distinct from waiting notifications.

Persistent data grew between goals and was never reset. The initial G4 observability check used a stale preserved smoke report and failed Loki correlation; a fresh smoke and full nine-target/63-query verification passed during the 10 requests/s step. That tiny normal cohort is a background-work limitation for the step, separate from its load population. Instrumentation overhead and shared host processes are not isolated. Microsecond/short lock waits may fall between samples. No single dominant query or production ceiling is asserted.

All expired unfinished/failed reports and late completions remain misses; draining does not erase them. API acknowledgement errors, if observed, stay separate from committed-record counts. The guard handles replaceable publication state; PostgreSQL fencing remains the result correctness boundary. Queue/guard TTL, single-node storage, synthetic dependency behavior, finite run duration and local forwarding limit extrapolation.

## Final measured results

Evidence: evidence/g4/comparison-20261011T232836Z/, source 0fb2942, UTC 2026-10-11 23:28:37–23:54:34. All fourteen resource histories contain samples; nonempty history does not imply continuous telemetry. No API/HTTP/worker/PostgreSQL restart increase occurred during the load comparison. After high-rate drain, all 10,794 committed reports completed with the same 8,862 misses retained; no terminal business failure was overwritten. Final drained high-rate processing p99 was 155.28 seconds.

| Rate/duration | Scheduled requests | HTTP/client error ratio | Client p99 | Deadline success | Result |
| --- | ---: | ---: | ---: | ---: | --- |
| 10 requests/s, 180 seconds | 1,800 | 0% | 66.26 ms | 1,800/1,800 | Passed |
| 30 requests/s, 180 seconds | 5,400 | 0% | 170.50 ms | 5,400/5,400 | Passed |
| Nominal 60 requests/s, 180 seconds | 10,800 | 0.898% | 14,797.14 ms | 1,932/10,794 | Failed; generator limited |
| 30 requests/s, 600 seconds | 18,000 | 0% | 251.35 ms | 18,000/18,000 | Passed confirmation |

The confirmed passing rate remains 30 requests/s in this local configuration. G4's lower confirmation processing latency than G3 cannot be attributed solely to deduplication: physical notification drain was added, data grew and other conditions differ. HTTP latency increased while still passing the provisional lab threshold. Neither the high-rate failure nor this confirmation establishes a precise or production capacity ceiling. Higher rates/longer high-rate confirmation are unexecuted.

## Observability gap and resource pressure

Supplemental scrape-history.json shows 54 five-second samples with exporter up=0, approximately 23:36:57–23:41:22 UTC. TelemetryUnavailable actually entered pending/firing during that interval; its retained historical evaluation and recovered final checks are separate from fixture tests. No real 30-day availability compliance can be established with this missing telemetry. Business/client results come from raw client samples and PostgreSQL cohorts and remain visible despite the scrape gap.

Exporter-backed queue gauges sampled only an early high-rate maximum of 278 waiting notifications and missed the later backlog. A directly executed atomic Redis snapshot at approximately 23:39:09 observed 3,069 ready/two reserved/zero delayed; it is preserved separately in queue-point-observation.json from the original tool output. It is a point observation, not an exhaustive peak or proof of every payload's multiplicity. Do not present 278 as the true maximum. Native FPM/cAdvisor collection follows independent targets, but report/dispatch/Redis gauges share the SQL exporter and its missing intervals.

PostgreSQL CPU reached approximately its two-core quota during the overloaded client interval, with throttling, report/metrics locks and WAL waits in sampled activity. API CPU maxima were approximately 0.80/0.77 cores; the confirmation database maximum was around 1.55 cores. Resource-analysis.json contains per-stage samples. CPU quotas, growing SQL dataset/reconciliation work and exporter query pressure are correlated limiting factors; no single query or the deduplication change alone is proven causal. Default versions, main children and limits were unchanged. The known low-rate duplicate mechanism was fixed; high-rate latency/timeliness and telemetry resilience remain open risks requiring another measured goal.
