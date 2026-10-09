# Error-budget policy (provisional local lab)
Every decision first checks telemetry completeness and eligible volume. Zero traffic or missing history is insufficient evidence; missing telemetry triggers investigation, not permission to release. No automation merges, deploys remote systems or rolls back.

A critical multi-window burn (2%/1h or 5%/6h) calls for immediate triage: preserve correlated evidence, identify affected user outcomes, check DB/Redis/workers/dependency, apply a documented reversible local mitigation. Freeze risky lab changes during investigation. A warning (10%/1d or 10%/3d) prioritizes reliability work over features, assigns follow-up and reviews recurrence.

If the actual rolling budget is exhausted, pause risky releases until recovery and remediation have been reviewed by the human owner/reviewer. Below 25% budget remaining, prioritize identified reliability work and use smaller changes with explicit observation. Healthy telemetry and recovered burn alone do not erase past misses or restore a spent budget. Emergency reliability fixes may proceed under existing local authorization with tests and recorded evidence; remote release/merge always requires separate human approval.

For G1 all targets remain provisional. Accelerated demonstrations may trigger local investigation but never establish a real monthly release gate. renanfenrich owns development; octavariumdigitalpartners approves PRs; Codex stops READY FOR HUMAN REVIEW.
