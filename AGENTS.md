# G1 operating rules

Scope: local asynchronous Laravel report service, dedicated Compose project and kind cluster `laravel-reliability-lab`. No frontend, cloud, AWS, billing, tenancy, AI or remote infrastructure deployment. Pushes/publication require explicit human authorization. Change only this repository and its dedicated resources. Never use an implicit Kubernetes context.

renanfenrich owns development and Git flow; octavariumdigitalpartners is mandatory reviewer/approver. Stop at READY FOR HUMAN REVIEW. No merge without that approval. Conventional Commits per independently validated phase.

No secrets or personal data in Git. Synthetic inputs only. Generate local credentials into ignored `.env` and Terraform secret inputs. Never print them in evidence.

Commands: `make doctor dev-up dev-down cluster-up build deploy test smoke load-test verify teardown`. `make data-reset` is separately destructive and requires explicit human authorization. Teardown preserves persistent data by default. No privileged package installs.

Tests must exercise durable acceptance, queue failure recovery, duplicate delivery, retries and interruption against PostgreSQL/Redis. Save actual commands, UTC times, SHA, versions and outputs in evidence. Never fabricate results, hide failures, claim hosted CI passed without a run, describe this lab as production experience, or claim a short experiment achieves a 30-day SLO.

Resume from docs/status.md and docs/goals/G1.md; inspect Git status and current evidence before rerunning discovery. Update status after every phase, recording blockers and unexecuted checks. Order A application; B runtime; C observability/SLO; D experiments/evidence. Keep progress terse.

Host metrics: `make host-metrics-up host-metrics-down`; Linux user systemd collector reads /proc and project-only Docker stats. Bound to dedicated kind bridge, never expose Docker socket or host metrics to LAN. `make deploy` discovers gateway; teardown stops the project unit. Validate both Grafana dashboards through scripts/observability-check.py.

Local alert email: make rules, make alert-test, make mail-up/mail-down. Mailpit captures alerts@lab.test only; never configure relay/forwarding/external recipients under G1. Notification fixtures are not live SLO evidence. alert-test temporarily pauses scheduler and host collector and must restore both, retaining terminal failed reports and exported messages.

Release authorization: on 2026-10-11 the user approved G1 and explicitly requested a public repository under renanfenrich plus release 0.1.0. This authorizes initial repository creation, initial pushes and v0.1.0 release publication only. No merge or cloud deployment is authorized; subsequent changes retain the review gate.

Documentation language: use US English (en-US) for all new or updated repository documentation. Preserve commands, identifiers, measured values, evidence provenance, and explicit validation limits. Do not translate or rewrite historical raw logs to make them appear newly validated.

G2 authorization: define and execute docs/goals/G2.md locally on feat/g2-capacity-recovery. Preserve G1 evidence. Scope includes a supported HTTP runtime, service-wide local load tests, simultaneous worker interruption, private logical backup restored into a fresh isolated DB, and retained observability storage. Controlled recreation of only the named kind cluster is allowed after PostgreSQL backup and telemetry export; no live DB overwrite/data-reset. Never dump secrets or commit private backups. Resume G2 from docs/status.md; stop READY FOR HUMAN REVIEW without push/merge/publication.
