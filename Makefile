SHELL := /bin/bash
.PHONY: tunnel-token tunnel-up tunnel-down
tunnel-token:
	@python3 scripts/tunnel-token.py
tunnel-up tunnel-down:
	@./scripts/lab.sh $@
.PHONY: doctor build dev-up dev-down cluster-up deploy test smoke load-test verify teardown data-reset rules host-metrics-up host-metrics-down mail-up mail-down alert-test g2-backup g2-runtime g2-load g2-interruption
doctor build dev-up dev-down cluster-up deploy test smoke load-test verify teardown data-reset rules host-metrics-up host-metrics-down mail-up mail-down alert-test g2-backup g2-runtime g2-load g2-interruption:
	@./scripts/lab.sh $@
