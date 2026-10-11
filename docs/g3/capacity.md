# G3 local capacity comparison

Status: local comparison and confirmation completed; the failed 60 requests/s step is preserved. This is a workstation portfolio measurement, not production experience, a promised capacity target, or a 30-day SLO result.

## Before change

Evidence: evidence/g3/baseline-20261011T205333Z/, diagnostic harness source 8d644e7. The deployed application still had the G2 histogram writer and shared-pool probes; the exported manifests/pod snapshots identify that actual workload separately from the harness SHA. UTC 20:53:33–20:57:36 on 2026-10-11.

| Offered rate and duration | Scheduled requests | HTTP errors | Client p99 | Processing p99 | Expired deadlines met | Generator p99 delay |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 60 requests/s, 180 seconds | 10,800 | 0 | 424.22 ms | 39.02 s | 10,800/10,800 | 0.82 ms |

Both APIs served traffic: 5,407/5,393 responses. All accepted work drained. This standalone warm-pool step passed, unlike the failed 60 requests/s G2 sequences. It does not establish stable sustained throughput at that rate. G2's passing ten-minute 30 requests/s and failed 60 requests/s results remain in docs/g2/ and are not overwritten.

CPU range maxima in retained baseline histories: API containers approximately 0.62/0.60 cores, PostgreSQL 1.18 cores, workers 0.25/0.26 cores. API/database throttling was observed. These are samples, not exhaustive sub-second utilization or causal proof. Point query plans showed full table scans for deadline/lease work; sparse PostgreSQL activity samples did not establish dominant lock contention.

## Selected correction

Keep dependency versions, four main children, resource limits, gateway/client timeouts, simulator defaults, queue semantics and SLI labels unchanged. Separate liveness from the main pool, then replace per-bucket histogram writes with one atomic increment statement. Do not add an invented admission limit or scale resources. The changed diagnostics contribute their own collection overhead, which is not isolated experimentally.

The isolated 500-observation fixture reduced SQL statement count from 5,000 to 500, SQL time from 812.47 to 171.95 ms and wall time from 1.37349 to 0.41702 s. Every cumulative bucket/count/sum matched exactly. A single microbenchmark timing is not a service speedup guarantee. Evidence: metrics-benchmark-before/after/comparison.json under evidence/g3/; reproduction and rollback are in ADR 012.

## After-change method and measured result

The diagnostic harness source is 1fb4be9, with committed application/configuration fingerprints in the result. It reuses the G2 256-thread, 15-second-client-timeout generator, scheduled arrivals, serving-pod response checks and expired-cohort denominator. Runs use load traffic through the internal gateway, never Cloudflare. Steps are 10/30/60 requests/s for 180 seconds; stop on saturation or generator limitation, drain every accepted cohort, then confirm an observed passing rate for 600 seconds. Higher rates are deliberately outside this G3 bounded comparison, so a fully passing sequence still does not measure a precise ceiling.

Evidence: evidence/g3/comparison-20261011T210320Z/, UTC 21:03:20–21:27:16 on 2026-10-11. All eleven resource histories contain samples.

| Offered rate and duration | Scheduled requests | HTTP errors | Client p99 | Processing p99 at deadline snapshot | Expired deadlines met | Generator p99 delay |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 10 requests/s, 180 seconds | 1,800 | 0.00% | 47.48 ms | 0.05 s | 1,800/1,800 | 0.49 ms |
| 30 requests/s, 180 seconds | 5,400 | 0.00% | 47.93 ms | 0.13 s | 5,400/5,400 | 0.36 ms |
| 60 requests/s, 180 seconds | 10,800 | 0.00% | 4019.53 ms | 89.25 s | 6,430/10,800 | 1.67 ms |
| 30 requests/s, 600 seconds | 18,000 | 0.00% | 134.68 ms | 23.26 s | 18,000/18,000 | 0.43 ms |

The 60 requests/s step **failed** latency/timeliness: only 74.71% of responses were within 500 ms, and 59.54% of committed reports met their 60-second deadline. All 10,800 submissions were acknowledged/committed, but 4,370 deadlines were missed. At the deadline snapshot 1,567 reports were unfinished. Every accepted report subsequently completed; the final drained-cohort processing p99 was 98.63 seconds, without repairing any missed deadline. The harness observed accepted-report drain about 42 seconds after the deadline snapshot, then started the confirmation. This is drain of business records, not proof that every stale Redis notification has been consumed.

Both API pods served the 60 requests/s step (5,374/5,426) and the 30 requests/s confirmation (9,033/8,967). API, NGINX, worker and PostgreSQL restart counts did not increase anywhere in this comparison. All those workloads were ready at the end. No post-change HTTP 502/504 or healthy-pool liveness restart occurred in this bounded overload run, but there is no whole-service capacity gain claim: the standalone before-change 60 requests/s baseline passed and the after-change sequence failed. The highest tested rate confirmed for ten minutes remains **30 requests/s**, with 18,000 successful acceptances, zero HTTP errors, all responses within 500 ms and every processing deadline met.

## Bottleneck evidence and remaining hypotheses

At 60 requests/s the native main-pool queue reached 89/86 connections. API CPU peaked around 0.91/0.90 cores against one-core limits, while PostgreSQL reached 1.89 cores against its two-core limit; CPU throttling increased materially. PostgreSQL activity samples recorded transaction-ID locks, WAL waits and active report queries, with maximum observed transaction age approximately 1.05 seconds. The 15-second resource snapshots and five-second activity samples establish correlated resource/queue pressure, not precise attribution of a single dominant query.

Redis waiting notifications peaked at 10,193 during drain, while the corresponding durable pending gauge was 861. At confirmation start Redis still had approximately 5,910 waiting notifications while the pending gauge was 147. Metric sampling is not an atomic snapshot, but this sustained surplus plus the confirmed five-second redispatch reservation mechanism indicates duplicate-notification amplification: pending rows can be published repeatedly before the first notification is consumed. This does not duplicate committed results, but consumes queue/database work and confounds recovery/load comparisons. Raw queue payloads were not exported, so per-message multiplicity is unverified. The protocol intentionally waited for accepted records to finish, not for notification depth to reach zero. That residual work is a measurement limitation, not suppressed evidence.

Confirmed improvements are independent probe semantics, visibility into these constraints and the 90% fixture SQL-statement reduction. No claim says batching eliminated shared counter serialization, CPU throttling, duplicate notifications or high-rate deadline misses. Follow-up candidates require separate measured changes: dispatch deduplication/backlog management, isolated query/lock profiling, and only then a justified admission policy or resource change. No new rate target was invented.

## Host resources

Host: Intel Core i7-13620H, 16 logical CPUs, 33,374,842,880 bytes RAM (about 31.08 GiB), 8 GiB swap, approximately 83.93 GB free on the repository filesystem at run start. During the comparison summed pod/container working sets peaked around 2.33 GiB; available host memory stayed approximately 19.66–20.26 GiB. Host non-idle CPU ranged approximately 0.97–6.95 cores. Host activity includes unrelated processes; the kind Docker container includes pods and must not be added again to pod totals. Resource limits/configuration, dependency versions and image IDs are recorded in the result and evidence/g3/runtime-versions.json. These observations support workstation practicality, not indefinite storage/memory stability.

## Measurement limits

The before step was a standalone warm-pool workload while the after sequence follows a source rollout and lower-rate warm-up. Persistent report data grows between runs and was never reset or restored over the live database. Builds and an isolated Compose microbenchmark overlapped the baseline; a bounded read-only query-plan snapshot ran during the after-change 30 requests/s step. Both use the same host, so background work and instrumentation are comparability limits.

Five-second PostgreSQL activity sampling can miss short waits. The first baseline parser failed on multiline JSON; its errors and corrected supplemental samples remain visible. Native FPM counters reset on process replacement; PostgreSQL-backed application counters do not. Main-pool waiting, proxy/network and metric writes are absent from the narrower middleware latency measurement, so client timings govern this capacity comparison. The native status pool can remain alive while main children are blocked; readiness and useful progress are separate.

All failed/unfinished accepted reports count once their deadlines expire, and later completions never erase misses. Client acknowledgement failures can coexist with committed records; retain both populations. The shared workstation, single-node database/cluster, local forwarding, synthetic simulator and finite observation period prevent production extrapolation or monthly SLO claims.
