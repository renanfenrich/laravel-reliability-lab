# G2 measured local capacity

The experiment uses the internal gateway and Kubernetes API Service, reaching both NGINX/PHP-FPM replicas. It records scheduled-arrival client latency, response identity, HTTP status, generator delay, and database acceptance cohorts. This is synthetic workstation evidence, not production capacity or a rolling 30-day SLO. Source: 739bcf0fbdda655f23a339f5a4e9aff6fd4fbb62. Raw evidence: evidence/g2/load-20261011T190929Z/.

## Three-minute exploratory steps

| Offered requests/s | Requests | HTTP errors | Client p99 | Completed within 60 s | Generator p99 lateness |
|---|---:|---:|---:|---:|---:|
| 10 | 1,800 | 0 | 62.6 ms | 100% | See step-10.json |
| 30 | 5,400 | 0 | 63.53 ms | 100% | 0.53 ms |
| 60 | 10,800 | 982 (9.09%) | 8,383.94 ms | 67.57% | 1,214.09 ms |

At the 60 requests/s step, 9,827 rows were committed, versus 9,818 successful acceptance responses. Thus nine committed reports lacked a successful response; clients must reuse their idempotency keys after ambiguous responses. The expired cohort had 6,640 on-time completions and 3,187 misses, including 951 still unfinished at measurement. Later completion must not erase these misses. All observed HTTP errors were 502 responses. Both replicas served traffic in every step.

The 60 requests/s step failed several user-outcome thresholds and also exceeded the generator delay bound. Consequently it does not establish a precise server-only saturation ceiling. Increasing load stopped; rates 90/120/180/240 were unexecuted. The previous passing rate, 30 requests/s, was selected for a separate ten-minute confirmation after the backlog drained. The ten-minute confirmation passed: 18,000 requests, 29.9997 successful acceptances/s, zero errors, all client responses within 500 ms, client p99 112.51 ms, and all 18,000 accepted reports completed within 60 seconds. End-to-end p99 was 21.34 seconds; generator scheduling p99 delay was 0.433 ms. Pod distribution was 8,901/9,099. This establishes 30 requests/s for this measured configuration and interval, not a precise maximum or long-term guarantee. The confirmation ran from 19:22:15Z to 19:32:15Z and cohort verification finished at 19:33:15Z.

## Measurement contract

Each request has a unique synthetic idempotency key, bearer authentication, traffic=load, a 15-second client timeout, and no automatic HTTP/upstream retry. The generator uses up to 256 threads. Three-minute steps wait until every accepted deadline has expired. Client scheduling p99 delay above 250 ms marks generator limitation. Exploratory stopping criteria are HTTP errors above 1%, fewer than 99% of requests within 500 ms, or fewer than 99% accepted reports completed within 60 seconds. The lab policy availability objective remains 99.9%; passing steps observed zero errors. Load and intentional faults stay excluded from normal SLO event populations.

The committed cohort includes accepted reports without successful client acknowledgments, failed reports, and unfinished reports after expiry. Client latency includes local forwarding, gateway, NGINX queueing, FPM boot/application work, database interactions, and response transport. Middleware latency alone cannot measure this whole path.

The result artifact records host hardware, full workload resource configuration, source SHA, UTC times, raw requests, API identity distribution, and Prometheus resource history. Container CPU sums can include pod aggregates; inspect container attribution before interpreting limits. The host runs Compose and unrelated background work as well as kind. No capacity target was invented, and no improvement can be attributed to FPM alone: the gateway, replica distribution, and runtime/resource configuration also changed from G1.

## Resource evidence and bottlenecks

Host: Intel Core i7-13620H, 16 logical CPUs, 33,374,842,880 bytes RAM, 85,107,216,384 bytes available filesystem space at experiment start. APIs each had four static FPM children, one-core FPM limit, and a separate 0.5-core NGINX limit. The gateway had one core; two workers and one scheduler used the same PostgreSQL/Redis and single kind node. Exact requests/limits and images are in result.json and evidence/g2/images.json.

At the failing 60 requests/s step, sampled one-minute FPM CPU maxima were 0.932 and 0.722 cores; PostgreSQL reached 1.530 cores. CPU throttled-time rates increased for both APIs and PostgreSQL. These rates are aggregate throttled seconds per second, not a percentage of HTTP failures. One API lost readiness during the submission interval. Kubernetes events explicitly record liveness timeouts at 19:18:29Z and container restarts at 19:19:39Z/19:19:43Z; gateway readiness failed shortly afterward. This confirms that saturated request handling interfered with probes and API availability. It does not establish the proportion of errors caused by CPU, SQL contention, FPM queueing, or restarts. Isolating those mechanisms requires further profiling and separate probe design experiments.

During the ten-minute confirmation, FPM maxima were 0.396/0.410 cores, PostgreSQL 0.790 cores, and all sampled API readiness values were healthy. Available host memory never fell below 20.13 GiB. Across the entire experiment, sampled API working-set maxima were approximately 181.3/179.4 MiB and Grafana 247.3 MiB. Whole-host peak active CPU was approximately 7.96 cores, including unrelated work. Observed evidence does not indicate host RAM exhaustion; the narrower application/database/queue/probe path remains the likely constraint. Shared durable metric writes are a hypothesis to profile, not a demonstrated root cause.

The original reports history query mistakenly used lab_reports_current and returned no series. That artifact is preserved; supplemental-history.json captures the correct lab_reports and overdue metrics, per-container CPU, readiness, restarts, and firing alerts over the identical interval. Future harness runs use the corrected name. resource-summary.json separates measured submission intervals. No firing alert series was observed over this load interval; normal SLO burn alerts exclude this synthetic traffic, and successful recovery does not prove notification delivery for every failure mode. G1 deterministic alert and local email evidence remains separate.

Recommended follow-up: isolate lightweight process probes from the application request pool, profile PostgreSQL transaction/metric contention, and repeat the same fixture with one configuration change at a time. Preserve the failed 60 requests/s cohort and ambiguous acknowledgments. Do not claim 60 requests/s is sustainable or invent an interpolated capacity ceiling.

## Live viewing rerun

A subsequent user-requested rerun with external Grafana viewing again confirmed 30 requests/s for ten minutes: 18,000 acceptances, zero errors, client p99 89.00 ms, completion p99 22.89 seconds, all deadlines met. Its 60 requests/s step failed and was generator-limited; preserve both runs rather than averaging away failure. See [rerun report](load-rerun-20261011.md) and evidence/g2/load-20261011T200936Z/.
