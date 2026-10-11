# Consistent logical backup and isolated restore

Run `python3 scripts/g2-backup.py` against the explicit dedicated cluster. The script holds an exported repeatable-read PostgreSQL snapshot while calculating canonical report/metric/migration fingerprints and running pg_dump. This avoids comparing a moving live database with a different backup snapshot.

Custom-format dumps stay private in ignored `.runtime/backups` (directory 0700, file 0600). Only synthetic-data counts, checksums, timings, SHA, and an example completed result are exported under `evidence/g2/backup-ID`. The script verifies the target database name is new before creating `g2_restore_HEX`, uses pg_restore with exit-on-error, compares all fingerprints, and invokes application readiness with DB_DATABASE set to the isolated restored database. Live data is never overwritten. The dump and isolated DB remain available for inspection; deleting them requires an explicit project-scoped cleanup action.

Limits: same instance/local disk, logical snapshot only, no point-in-time recovery, off-host storage, role/credential backup, or arbitrary disaster guarantee. Snapshot RPO is the dump's snapshot time; elapsed restore is this exercise's duration, not a contractual RTO. Preserve host PostgreSQL directory during teardown. Do not copy a running physical data directory as a backup.
