SHELL := /bin/bash
.PHONY: doctor build dev-up dev-down cluster-up deploy test smoke load-test verify teardown data-reset rules host-metrics-up host-metrics-down mail-up mail-down alert-test g2-backup g2-runtime
doctor build dev-up dev-down cluster-up deploy test smoke load-test verify teardown data-reset rules host-metrics-up host-metrics-down mail-up mail-down alert-test g2-backup g2-runtime:
	@./scripts/lab.sh $@
