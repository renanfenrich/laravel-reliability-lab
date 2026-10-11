# Project-specific external Grafana access

The user authorized Cloudflare Tunnel access separately from G2's local experiments. User-provided tunnel name: `laravel-reliability-lab`. Hostname: `lrl-grafana.octavarium.com.br`. The published HTTP origin should be `http://192.168.1.9:13000`, the current project Grafana forward. No database, Redis, Prometheus, Loki, Docker socket, or SMTP route is authorized.

An unauthenticated Chrome request to the HTTPS hostname displayed the Cloudflare Access email/PIN login for `lrl-grafana`. This confirms an Access challenge, not the allowed-email policy, tunnel health, correct backend routing, or authenticated dashboard access. At the initial check, no account login or connector credential was available locally. The user subsequently supplied a test credential: the connector registered four connections and the public hostname still required Access. See evidence/cloudflare/connection.json. Authenticated external dashboard access and the actual allowed-identity policy remain unverified.

## Connect the notebook

In Cloudflare, open the **laravel-reliability-lab** tunnel's connector setup and copy only its tunnel token. In an interactive notebook terminal (or an SSH terminal with a TTY):

```sh
cd /home/renanfenrich/Code/laravel-reliability-lab
make tunnel-token
make tunnel-up
```

The token prompt is hidden. The helper stores it only in ignored `.runtime/cloudflare/tunnel-token`, mode 0600, under a mode 0700 directory. It refuses implicit replacement. Never paste credentials into chat, source, logs, or shell command arguments. The binary is project-local cloudflared 2026.10.0, verified against the official release digest; no privileged installation is needed.

`tunnel-up` checks token ownership/permissions, binary SHA256, and local Grafana health, then starts the project-specific user systemd unit `laravel-reliability-lab-tunnel.service`. It uses `--token-file`, disabled auto-updates, and bounded restart delay. Repeated starts reuse an active unit. This transient unit is not a boot-persistent service; start it again after reboot/login as needed. The Grafana forward must remain running, and its current LAN IP must remain valid. Do not change shared Cloudflare resources or existing unrelated tunnels.

```sh
systemctl --user is-active laravel-reliability-lab-tunnel.service
make tunnel-down
```

Teardown stops only this project's tunnel unit and preserves the private credential. Stopping the connector does not delete remote DNS or Access configuration. To revoke remote access, disable the specific published route or rotate the specific tunnel token in Cloudflare.

## End-to-end verification

After connector startup, check **Healthy** in Cloudflare. Test the HTTPS hostname over cellular data: complete the allowed-email Access challenge, then the Grafana login; inspect both provisioned dashboards and live queries. Also verify that unauthenticated access still requires Access. Do not remove the Access policy or Grafana authentication to make a test pass. Keep screenshots free of credentials/OTP values.

If Cloudflare returns 1033, inspect connector status. If it returns 502, check the Grafana forward and the route's origin. An Access denial requires checking the allowed-identity policy, not bypassing authentication. Avoid external load traffic during internal capacity experiments. Official references: [Tunnel setup](https://developers.cloudflare.com/tunnel/get-started/) and [Access application](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/self-hosted-public-app/).
