SHELL := /bin/bash
.PHONY: tunnel-token tunnel-up tunnel-down
tunnel-token:
	@python3 scripts/tunnel-token.py
tunnel-up tunnel-down:
	@./scripts/lab.sh $@
.PHONY: doctor build dev-up dev-down cluster-up deploy test smoke load-test verify teardown data-reset rules host-metrics-up host-metrics-down mail-up mail-down alert-test g2-backup g2-runtime g2-load g2-interruption
doctor build dev-up dev-down cluster-up deploy test smoke load-test verify teardown data-reset rules host-metrics-up host-metrics-down mail-up mail-down alert-test g2-backup g2-runtime g2-load g2-interruption:
	@./scripts/lab.sh $@

.PHONY: g3-baseline g3-load g3-probes g3-runtime
g3-baseline:
	@python3 -u scripts/g3-load.py baseline
g3-load:
	@python3 -u scripts/g3-load.py comparison
g3-probes:
	@python3 -u scripts/g3-probes.py
g3-runtime:
	@python3 scripts/g3-runtime-contract.py

.PHONY: g3-interruption
g3-interruption:
	@python3 -u scripts/g2-interruption.py g3

.PHONY: g4-pause-before g4-pause g4-load g4-interruption
g4-pause-before:
	@python3 -u scripts/g4-pause.py before
g4-pause:
	@python3 -u scripts/g4-pause.py after
g4-load:
	@python3 -u scripts/g3-load.py comparison g4
g4-interruption:
	@python3 -u scripts/g2-interruption.py g4

.PHONY: g4-preclaim
g4-preclaim:
	@python3 -u scripts/g4-preclaim.py
