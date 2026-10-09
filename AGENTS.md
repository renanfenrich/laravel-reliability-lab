# G1 operating rules
Scope: local asynchronous Laravel report service, dedicated Compose project and kind cluster `laravel-reliability-lab`. No frontend, cloud, AWS, billing, tenancy, AI, remote deployment, pushes or publication. Change only this repository and its dedicated resources. Never use an implicit Kubernetes context.

renanfenrich owns development and Git flow; octavariumdigitalpartners is mandatory reviewer/approver. Stop at READY FOR HUMAN REVIEW. No merge without that approval. Conventional Commits per independently validated phase.

No secrets or personal data in Git. Synthetic inputs only. Generate local credentials into ignored `.env` and Terraform secret inputs. Never print them in evidence.

Commands: `make doctor dev-up dev-down cluster-up build deploy test smoke load-test verify teardown`. `make data-reset` is separately destructive and requires explicit human authorization. Teardown preserves persistent data by default. No privileged package installs.

Tests must exercise durable acceptance, queue failure recovery, duplicate delivery, retries and interruption against PostgreSQL/Redis. Save actual commands, UTC times, SHA, versions and outputs in evidence. Never fabricate results, hide failures, claim hosted CI passed without a run, describe this lab as production experience, or claim a short experiment achieves a 30-day SLO.

Resume from docs/status.md and docs/goals/G1.md; inspect Git status and current evidence before rerunning discovery. Update status after every phase, recording blockers and unexecuted checks. Order A application; B runtime; C observability/SLO; D experiments/evidence. Keep progress terse.
