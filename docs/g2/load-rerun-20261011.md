# Live load rerun observed through external Grafana

The user requested a repeat while watching Grafana through Cloudflare. `make g2-load` ran from 2026-10-11T20:09:36Z to 20:33:35Z, source commit `0b6e905aa1d4a08fb3d8247abf6e732e5d21b522`. The existing G2 configuration/images were reused, with both API replicas behind the internal gateway. Cloudflare carried dashboard viewing; the load generator did not send API traffic through Cloudflare. The run sent 36,000 scheduled synthetic requests classified as load, separately from normal SLO eligibility. No 30-day SLO or production capacity is established.

| Offered requests/s | Submission duration (s) | Requests | HTTP error ratio | Client p99 | Accepted reports within 60 s | Generator |
|---|---:|---:|---:|---:|---:|---|
| 10 | 180 | 1,800 | 0.00% | 61.54 ms | 100.00% | Within bound |
| 30 | 180 | 5,400 | 0.00% | 63.46 ms | 100.00% | Within bound |
| 60 | 180 | 10,800 | 8.49% | 9417.42 ms | 53.18% | Limited |
| 30 confirmation | 600 | 18,000 | 0.00% | 89.00 ms | 100.00% | Within bound |

## Observed failure and recovery

The 60 requests/s step failed: 772 HTTP502 and 145 HTTP504 responses; client p99 9.417 seconds. The 9,891 committed reports included eight without successful acknowledgment, so retrying clients must reuse their idempotency keys. Once every accepted deadline expired, 5,260 met the deadline and 4,631 missed it. At that measurement, 1,349 were still unfinished and none terminally failed. Later completions do not erase misses. Generator scheduling p99 delay reached 8.211 seconds, so this is not a precise server-only capacity ceiling. API restarts were observed during that step. No higher exploratory rates were executed.

After the saturated backlog drained, the ten-minute 30 requests/s confirmation passed: 18,000 successful acceptances, 29.9991 accepted requests/s, zero errors, all client responses within 500 ms, and all 18,000 accepted reports completed within their 60-second deadlines. End-to-end completion p99 was 22.893 seconds. Generator p99 scheduling delay was 0.374 ms. Both API replicas were used: 8,976/9,024 responses. Every deadline expired before the cohort result was recorded.

Post-run smoke verified authenticated committed acceptance, concurrent idempotency, a worker result, and PostgreSQL correlation. The observability check verified seven healthy targets and all 55 provisioned dashboard metric/log queries. All 15 deployments were ready. The project tunnel and Grafana forward remain running.

## Interpretation and evidence

This repeats the observed ten-minute success at 30 requests/s. The previous confirmation had client p99 112.51 ms and completion p99 21.34 seconds, versus 89.00 ms and 22.89 seconds here. The failing 60 requests/s step had different error/timeliness values; accumulated data, background activity, active dashboard viewing, queue/probe interactions, and generator delay prevent attribution to one cause or an interpolated maximum. No application/runtime optimization was made during this rerun. Preserve both runs.

Raw evidence: `evidence/g2/load-20261011T200936Z/`: step/confirmation request samples, complete expired cohorts, source SHA, host resources, workload configuration, six nonempty Prometheus resource histories, recovery events, smoke/observability logs and deployment readiness. `docs/g2/capacity.md` preserves the original G2 report. `evidence/cloudflare/browser-verification.json` records read-only Chrome verification of authenticated external dashboard, tunnel Healthy and the requested identity policy without committing the personal email or credential.
