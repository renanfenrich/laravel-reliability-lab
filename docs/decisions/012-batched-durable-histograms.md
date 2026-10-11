# Batch histogram updates without weakening durable aggregation

G3's local baseline showed PostgreSQL CPU up to 1.18 cores with throttling, API CPU approximately 0.60–0.62 cores with throttling, and no sustained dominant lock wait established by sparse activity samples. Histogram observation wrote one SQL statement per eligible cumulative bucket, then count and sum. A reproducible isolated microbenchmark measured 5,000 statements for 500 observations, 812.47 ms SQL time and 1.37349 s wall time. These identify avoidable hot-path work, not proof that every overload episode has one database cause.

Keep PostgreSQL authoritative and the exporter singleton. Construct the same bounded series and submit all increments in one INSERT ... ON CONFLICT statement, with sorted series keys. Atomicity preserves the enclosing acceptance/completion transaction, cumulative buckets, count and sum; rollback must discard all increments. No buffering, external metrics replica, periodic flush, lost increments, or new dependency is introduced.

After batching, the same isolated benchmark measured 500 statements, 171.95 ms SQL time and 0.41702 s wall time, with identical series values. This is a 90% statement reduction for that fixture; the timing is a single local observation, not a statistical or whole-service speedup guarantee. Reproduce after migrating only Compose lab_test:

```sh
docker compose run --rm --no-deps -e DB_DATABASE=lab_test api php artisan migrate --force
docker compose run --rm --no-deps -e DB_DATABASE=lab_test \
  -v "$PWD/scripts/g3-metrics-benchmark.php:/tmp/benchmark.php:ro" api php /tmp/benchmark.php
make test
```

The script refuses other databases. No live reports are deleted. Application tests verify cumulative boundary buckets, infinite bucket/count/sum, transaction rollback, duplicate delivery, fenced recovery and visible failure. Database session diagnostics expose only three operation classes and five wait classes; raw query text is never a label. Native pg_stat_database counters and Redis queue depth add context without restarting PostgreSQL or adding extensions. PostgreSQL [statistics semantics](https://www.postgresql.org/docs/18/monitoring-stats.html) include asynchronous cumulative updates and cannot resolve sub-sample waits.

Full-scan deadline/lease queries were observed but their point durations alone did not justify adding indexes in this correction. No FPM child/CPU increase or admission limit was selected: the latest baseline passed and an invented limit could conceal overload or reduce useful acceptance. Valid overload errors remain bad outcomes under the existing eligible population; experiment traffic is kept separate. SLO definitions and buckets are unchanged. Source rollout resets native FPM counters; rate before sum, and preserve database-backed application counters.

Rollback restores the previous histogram writer through a source/image rollout; it requires no schema/data migration. It restores the measured statement overhead as well. Comparable load and failure evidence is in docs/g3/capacity.md and evidence/g3/; do not infer a result before execution.
