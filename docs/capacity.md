# Measured local capacity — G1
CONFIRMED: highest passing tested burst was40 offered requests/s; the next refined point50 requests/s breached the provisional client-latency threshold. This is a bracket between tested points, not an invented capacity target or sustained production capacity.

Initial experiment source `2b99c860476b58d57596e07c64a7ad890295b5d5`, UTC 2026-10-09T20:23:42Z to 2026-10-09T20:32:30Z. Refined generator source `c2236de1b58aee5faf64bf3173854ef2468507b7`; deployed application remained `2b99c860476b58d57596e07c64a7ad890295b5d5`. Raw samples/configuration: evidence/experiments.json, capacity-retake.json and capacity-50.json. Final changes after measurement only improve scheduler log routing and bound init-container resources; no rebenchmark of the final documentation/operational commit is claimed.

## Method and results
Authenticated synthetic POST, unique idempotency keys,20-second scheduled-arrival bursts, then wait for every accepted deadline to expire. Two API replicas exist, but loopback port-forward selects one pod; four PHP CLI HTTP worker processes share its1-core/384Mi limit. Two queue-worker replicas each have1-core/384Mi limit; PostgreSQL2-core/512Mi, Redis1-core/256Mi. The generator originally had128 threads; refinement used512. SQL counts all accepted reports, including failed/unfinished after60s. All healthy/refined cohorts below completed before deadline, zero failed/unfinished. No offered-rate extrapolation or long-duration SLO attainment.

| Offered rps | Requests | Effective rps | Client p99 ms | HTTP errors | <=500ms | Processing <=60s | Send lateness p99 ms |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2 | 40 | 2.05 | 51.1 | 0.00% | 100.00% | 100.00% | 0.39 |
| 10 | 200 | 10.02 | 66.7 | 0.00% | 100.00% | 100.00% | 0.39 |
| 30 | 600 | 29.99 | 64.9 | 0.00% | 100.00% | 100.00% | 0.41 |
| 40 | 800 | 39.97 | 48.3 | 0.00% | 100.00% | 100.00% | 0.36 |
| 50 | 1000 | 31.73 | 11499.0 | 0.00% | 6.00% | 100.00% | 1.28 |

Healthy normal baseline:40 unique reports at2 offered rps, client p99 61.3ms, completion p99 86.2ms, zero HTTP errors and40/40 deadline successes. Small samples cannot establish99.9% availability statistically or over30 days.

## Bottleneck interpretation
CONFIRMED: at50 rps the sender p99 lateness was1.28ms (below250ms invalidation threshold), responses p99 were11.50s, effective throughput31.73 rps, and only6% of client responses met500ms. All1000 accepted reports completed within60s; completion p99 was243.8ms. The selected API showed CPU CFS throttling up to 2.005 throttled-seconds/s (summed across processes; not a wall-clock percentage). PostgreSQL/worker CPU was lower and processing after acceptance stayed fast.

INDICATION: the constrained HTTP admission/PHP execution path is the limiting part of this workload, rather than asynchronous processing. HYPOTHESIS: framework bootstrap, shared metric writes and a1-core CLI-server quota jointly cause the capacity knee. CPU throttling is correlated evidence, not proof of each component's individual contribution. No profiler, metric-write ablation, load-balanced two-pod test or production web-server comparison was executed. Middleware latency omits queueing/bootstrap before middleware and therefore under-represents client latency at saturation; front-door instrumentation would be needed for broader user-perceived latency SLOs.

## Invalid and limited probes retained
The pre-framing2-rps probe had ~1s total client time while first byte arrived in8.7ms; waiting for EOF through port-forward made it INVALID for estimating service saturation. Content-Length fixed the transport framing; regression and direct client probes passed. See experiments-before-framing.json and response-framing.json.

The original60-rps/128-thread probe had p99 send lateness13.85s. A512-thread60-rps retake still had868ms send lateness and7.33% client errors; it remains sender-limited for precise offered-rate attribution. Neither replaces the valid40/50 bracket. Failures/timeouts remain in samples and are never filtered away. The refined50-rps test has no client-generator ceiling evidence by the stated lateness check. It is still one short burst with cooldown, not steady-state capacity.

## Resources and limits
Host initially31Gi RAM,25Gi available,96Gi free disk (doctor.log); CPU model/count is in experiments.json host snapshot. Measured pod working-set sum at the original experiment end: 740.6MiB, excluding control plane/node overhead. Docker kind-node memory sample is retained in experiments.json docker_resources; an additional observed post-run sample was2.058GiB. Prometheus range data retains CPU, throttle, queue-state and memory observations; local NVMe/filesystem, other workstation activity, process startup and port-forward overhead limit portability. Declarative5Gi hostPath storage is not an enforced disk quota. PostgreSQL/Redis are single-node, with no HA/backup validation. Only synthetic fixed-size reports were tested.

NEXT: use a production-intended HTTP runtime/edge metric point and service-wide load balancing in a separately authorized goal, profile the API, test sustained rate/cohort behavior and then reconsider provisional SLOs. No production sizing recommendation is established here.

## Repetição solicitada em2026-10-11
Fonte a6a19af; evidence/load-20261011T175620Z/experiments.json,UTC17:56:20–18:03:28. Passaram2,10,30,40req/s (p99cliente48.7,55.2,56.8,63.6ms).50req/s teve1000requests,throughput29.25rps,p9913.97s,0erros,100%dosrelatóriosno prazo; sendernão limitante. Parada em50; taxas superiores não executadas. O bracket40/50 foi observado novamente, sem extrapolação sustentada. Coletorhost novo só foi instalado depois e não oferece histórico dessa repetição. Configuração/runtime completos preservados no JSON deste run.
