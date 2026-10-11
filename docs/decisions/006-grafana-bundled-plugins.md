# Keep Grafana plugins bundled with the pinned image

Grafana 13.2.3 bundles Prometheus/Loki plugins but enables asynchronous preinstallation/updates by default. Observed updater unregisters bundled plugins before replacement and fails on read-only root, producing plugin.notRegistered errors for every query. Disable GF_PLUGINS_PREINSTALL_DISABLED=true and GF_PLUGINS_PREINSTALL_AUTO_UPDATE=false in the Terraform-owned deployment. Plugins remain versioned by the pinned image; do not loosen root filesystem permissions or download floating plugin versions.

Reference: https://grafana.com/docs/grafana/latest/setup-grafana/configure-grafana/#preinstall_auto_update

Validation must query Grafana datasource health and all dashboard targets, not just dashboard provisioning and direct Prometheus/Loki endpoints. Empty alert series or latency without traffic can be legitimate; report state, memory and fresh correlated logs must contain frames. Grafana data/session DB is ephemeral and restart requires login; PostgreSQL report data remains untouched.
