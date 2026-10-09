# Validation ledger
No checks passed yet. Record pass/fail/unexecuted separately; outputs in evidence. Host discovery executed 2026-10-09. Application, runtime, observability and experiments pending. Hosted CI unexecuted.

Phase A PASS: `docker build`, migrations and `docker compose run --rm --no-deps api vendor/bin/phpunit`: 10 tests/39 assertions. Failed attempts retained and superseded, not suppressed. Real interruption/Kubernetes/observability/experiments/hosted CI remain unexecuted.

Phase B PASS: make cluster-up/deploy/smoke; evidence/cluster-up.log, deploy-B-recovered.log, smoke.json. Initial deployment failures recorded; PV/PVC metadata replaced while preserving host data. No default context changed.

Phase C PASS: make rules (short and long fixtures); make deploy/smoke; scripts/observability-check.py confirms four healthy targets, resource metrics, correlated worker logs and 15 Grafana panels. Deterministic simulated30d does not establish actual30d compliance. Full browser visual QA unexecuted.
