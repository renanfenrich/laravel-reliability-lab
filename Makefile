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
