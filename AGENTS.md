# G1 operating rules

Scope: local asynchronous Laravel report service, dedicated Compose project and kind cluster `laravel-reliability-lab`. No frontend, cloud, AWS, billing, tenancy, AI or remote infrastructure deployment. Pushes/publication require explicit human authorization. Change only this repository and its dedicated resources. Never use an implicit Kubernetes context.

renanfenrich owns development and Git flow. No separate reviewer account is required for this project. Stop at READY FOR HUMAN REVIEW unless the owner explicitly authorizes publication or merge; verify final-head CI before an authorized merge. Conventional Commits per independently validated phase.

No secrets or personal data in Git. Synthetic inputs only. Generate local credentials into ignored `.env` and Terraform secret inputs. Never print them in evidence.

Commands: `make doctor dev-up dev-down cluster-up build deploy test smoke load-test verify teardown`. `make data-reset` is separately destructive and requires explicit human authorization. Teardown preserves persistent data by default. No privileged package installs.

Tests must exercise durable acceptance, queue failure recovery, duplicate delivery, retries and interruption against PostgreSQL/Redis. Save actual commands, UTC times, SHA, versions and outputs in evidence. Never fabricate results, hide failures, claim hosted CI passed without a run, describe this lab as production experience, or claim a short experiment achieves a 30-day SLO.

Resume from docs/status.md and docs/goals/G1.md; inspect Git status and current evidence before rerunning discovery. Update status after every phase, recording blockers and unexecuted checks. Order A application; B runtime; C observability/SLO; D experiments/evidence. Keep progress terse.

Host metrics: `make host-metrics-up host-metrics-down`; Linux user systemd collector reads /proc and project-only Docker stats. Bound to dedicated kind bridge, never expose Docker socket or host metrics to LAN. `make deploy` discovers gateway; teardown stops the project unit. Validate both Grafana dashboards through scripts/observability-check.py.

Local alert email: make rules, make alert-test, make mail-up/mail-down. Mailpit captures alerts@lab.test only; never configure relay/forwarding/external recipients under G1. Notification fixtures are not live SLO evidence. alert-test temporarily pauses scheduler and host collector and must restore both, retaining terminal failed reports and exported messages.

Release authorization: on 2026-10-11 the user approved G1 and explicitly requested a public repository under renanfenrich plus release 0.1.0. This authorizes initial repository creation, initial pushes and v0.1.0 release publication only. No merge or cloud deployment is authorized; subsequent changes retain the review gate.

Documentation language: use US English (en-US) for all new or updated repository documentation. Preserve commands, identifiers, measured values, evidence provenance, and explicit validation limits. Do not translate or rewrite historical raw logs to make them appear newly validated.

G2 authorization: define and execute docs/goals/G2.md locally on feat/g2-capacity-recovery. Preserve G1 evidence. Scope includes a supported HTTP runtime, service-wide local load tests, simultaneous worker interruption, private logical backup restored into a fresh isolated DB, and retained observability storage. Controlled recreation of only the named kind cluster is allowed after PostgreSQL backup and telemetry export; no live DB overwrite/data-reset. Never dump secrets or commit private backups. Resume G2 from docs/status.md; stop READY FOR HUMAN REVIEW without push/merge/publication.

External-access authorization: on 2026-10-11 the user requested Cloudflare Tunnel access to this project. This narrowly supersedes the local-only boundary for a project-specific tunnel and its access policy; it does not authorize AWS, public databases, external SMTP, unrelated account resources, or Git publication. Confirm the hostname, intended services, and authorized identities before publishing a named route. Keep tunnel credentials ignored and private. Preserve the G2 baseline experiment without external traffic until measurement ends.

G2 publication authorization: on 2026-10-11 the user confirmed G2 completion and authorized publication and merge. Publish the completed G2 branch and open a ready PR under renanfenrich. The owner subsequently removed the separate reviewer requirement and explicitly authorized merging PR #2; check final-head CI before merging. The next request authorizes a G3 plan only, not G3 execution, deployment, or publication.

Reviewer policy update (2026-10-11): the owner explicitly removed the separate-account reviewer requirement for this project. Earlier reviewer-gate statements are superseded. This does not authorize G3 implementation or publication.

G3 authorization (2026-10-11): the owner explicitly authorized execution of docs/goals/G3.md locally. Use feat/g3-overload-resilience, preserve G1/G2 evidence and project data, measure before choosing a correction, and retain failed/generator-limited observations. No G3 push, PR, merge or release is authorized. The removed separate reviewer requirement remains removed.

G3 publication and G4 authorization (2026-10-11): the owner approved G3 and explicitly authorized push and merge after final-head CI. Open a ready PR and squash-merge it without a separate reviewer requirement. No release version/tag was requested. After confirmed G3 integration, define and execute G4 locally to address measured dispatch notification amplification while preserving durable acceptance, fencing, recovery and SLI populations. G4 publication/merge remains unauthorized.

G4 execution scope: docs/goals/G4.md on feat/g4-dispatch-deduplication after G3 integration. Controlled project worker pauses must restore the prior replica count in finally. Redis deletion tests are restricted to the isolated test database and uniquely named synthetic queues; no live flush/reset. Preserve business acceptance/fencing/deadlines and frozen earlier evidence. G4 publication is not authorized.

G4 publication and G5 authorization (2026-10-12): the owner approved G4 and explicitly requested merge and continuation. Publish the completed G4 branch, open a ready PR, and squash-merge after exact-head hosted CI passes. The project-specific removal of the separate reviewer requirement remains in force. No release/tag is requested. After integration, define and execute G5 locally from measured exporter SQL pressure and telemetry loss, preserving SLI populations, project data and prior evidence. G5 publication/merge requires later owner authorization.
