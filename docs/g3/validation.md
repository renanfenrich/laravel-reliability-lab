# G3 validation ledger

Status: in progress; no publication authorized. G2 evidence is preserved.

## Executed

- Dedicated project resources inspected: all 15 deployments ready; doctor completed. No unrelated contexts/services changed.
- Before-change metric microbenchmark: 500 histogram observations, 5,000 SQL statements, 812.47 ms measured SQL time, 1.37349 s wall time, expected cumulative buckets/count/sum retained. Isolated Compose lab_test database only. The first attempt lacked tables; its failure is preserved separately before migrations and successful retry.
- At 81,360 stored reports, EXPLAIN ANALYZE showed complete scans for deadline/lease work: approximately 7.3/6.3 ms, and a load/completed count approximately 12.4 ms. These are point observations, not attribution of the dominant capacity limit.
- Restricted PHP-FPM/NGINX configuration checks passed for an independent native status pool. Live deployment/probe tests remain pending.

## Pending

Comparable 180-second baseline; independent pool-saturation and actual process-failure tests; bounded diagnostics and corrected metric-write microbenchmark; after-change steps and ten-minute confirmation; application/rules/Terraform/schema/smoke/Grafana validation; incident/capacity/decision reports. Hosted G3 CI is unexecuted because publication is unauthorized.

## Limits and failed attempts

The first baseline PostgreSQL JSON parser selected only the last output line, failing on multiline JSON. Error samples are retained. A corrected supplemental collector runs concurrently; later runs use the corrected parser. Builds and an isolated Compose microbenchmark overlapped the baseline; host CPU is shared and these activities must be disclosed in capacity interpretation. No raw SQL or secret values are exported. No pg_stat_statements extension/restart, tracing service, database reset or live restore was used.
