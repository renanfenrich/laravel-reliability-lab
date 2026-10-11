# ADR 005 — deadline cohorts prevent survivor bias

Completed-only histograms would exclude stalled/failed reports and late completions could appear to improve historical timeliness. Instead, at scrape time PostgreSQL supplies total/met counts in fixed bounded deadline windows. All expired accepted reports enter their cohort. Immutable accepted/deadline/completed timestamps and terminal transitions prevent late completion from erasing a miss. Scheduler additionally stores final outcomes for audit. Direct cohort queries continue to count misses when scheduler is down, provided DB/exporter remain available.

API uses durable request-class counters/histograms, normal traffic only. Fault/load traffic has separate labels and evidence. Initial 30-day windows remain intended, never achieved by short tests. Long-window rule behavior is verified by deterministic promtool fixtures. Accelerated fault demonstration has its own name/severity/window. The initial routing destination was the local Prometheus console. ADR 008 adds local Alertmanager/Mailpit email capture; no external delivery is configured.

Sources: [Google SRE multi-window budget alerts](https://sre.google/workbook/alerting-on-slos/), [Prometheus rule testing](https://prometheus.io/docs/prometheus/latest/configuration/unit_testing_rules/). Contract and measurement gaps are explicit in docs/slo.md.
