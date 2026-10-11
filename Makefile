SHELL := /bin/bash
.PHONY: doctor build dev-up dev-down cluster-up deploy test smoke load-test verify teardown data-reset rules host-metrics-up host-metrics-down
doctor build dev-up dev-down cluster-up deploy test smoke load-test verify teardown data-reset rules host-metrics-up host-metrics-down:
	@./scripts/lab.sh $@
