#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export KUBECONFIG="$PWD/.kubeconfig"
cluster=laravel-reliability-lab
k() { "$PWD/.tools/kubectl" --kubeconfig "$KUBECONFIG" --context "kind-$cluster" "$@"; }
case "${1:-}" in
 doctor)
  for t in docker kind terraform python3 curl git; do command -v "$t"; done
  docker info --format '{{.ServerVersion}}'; docker compose version; kind version; terraform version
  kubectl config get-contexts --kubeconfig "$HOME/.kube/config" || true
  kind get clusters; free -h; df -h .; ss -ltn
  test "$(kind version | awk '{print $2}')" = v0.30.0
  terraform version -json | python3 -c 'import sys,json; assert json.load(sys.stdin)["terraform_version"] == "1.16.5"'
  ;;
 build)
  docker build -t laravel-reliability-app:g1 .
  docker build -t laravel-reliability-simulator:g1 simulator
  ;;
 dev-up)
  python3 scripts/init-env.py
  docker compose up -d --wait postgres redis simulator
  docker compose run --rm --no-deps api php artisan migrate --force
  docker compose up -d --wait api worker scheduler
  ;;
 dev-down) docker compose down ;;
 test)
  python3 scripts/init-env.py
  docker compose up -d --wait postgres redis
  docker compose exec -T postgres sh -c 'psql -U lab -tc "SELECT 1 FROM pg_database WHERE datname = '\''lab_test'\''" | grep -q 1 || createdb -U lab lab_test'
  docker compose run --rm --no-deps api vendor/bin/phpunit
  ;;
 cluster-up)
  test "$(kind version | awk '{print $2}')" = v0.30.0
  python3 scripts/init-env.py
  mkdir -p .tools .runtime/postgres
  if ! test -x .tools/kubectl; then
   curl -fsSL https://dl.k8s.io/release/v1.34.0/bin/linux/amd64/kubectl -o .tools/kubectl
   curl -fsSL https://dl.k8s.io/release/v1.34.0/bin/linux/amd64/kubectl.sha256 -o .tools/kubectl.sha256
   (cd .tools; echo "$(cat kubectl.sha256)  kubectl" | sha256sum --check); chmod +x .tools/kubectl
  fi
  .tools/kubectl version --client -o json | python3 -c 'import sys,json; assert json.load(sys.stdin)["clientVersion"]["gitVersion"]=="v1.34.0"'
  python3 - <<'PY'
import json,os
config={'kind':'Cluster','apiVersion':'kind.x-k8s.io/v1alpha4','name':'laravel-reliability-lab','networking':{'apiServerAddress':'127.0.0.1'},'nodes':[{'role':'control-plane','extraMounts':[{'hostPath':os.path.abspath('.runtime/postgres'),'containerPath':'/lab-postgres'}]}]}
open('.runtime/kind.json','w').write(json.dumps(config))
PY
  if kind get clusters 2>/dev/null | grep -qx "$cluster"; then
   test -f "$KUBECONFIG" || { echo 'Existing named cluster has no project kubeconfig; verify ownership manually.' >&2; exit 1; }
  else
   kind create cluster --name "$cluster" --image kindest/node:v1.34.0 --config .runtime/kind.json --kubeconfig "$KUBECONFIG" --wait 120s
  fi
  k get nodes
  ;;
 deploy)
  test -f .kubeconfig; k get nodes
  kind load docker-image --name "$cluster" laravel-reliability-app:g1 laravel-reliability-simulator:g1
  python3 scripts/render-infra.py
  terraform -chdir=infra init -input=false
  python3 scripts/tf-secrets.py
  terraform -chdir=infra apply -auto-approve -input=false -var-file=local.tfvars.json
  for name in $(python3 -c 'import json; print(" ".join(x["metadata"]["name"] for x in json.load(open("infra/manifests.json")).values() if x["kind"]=="Deployment"))'); do k -n lab rollout status deployment/"$name" --timeout=180s; done
  k -n lab exec deployment/api -- php artisan migrate --force
  k -n lab rollout restart deployment/api deployment/worker deployment/scheduler deployment/exporter
  for name in api worker scheduler exporter; do k -n lab rollout status deployment/"$name" --timeout=120s; done
  ;;
 smoke) python3 scripts/smoke.py ;;
 rules) docker run --rm --entrypoint promtool -v "$PWD/observability:/rules:ro" prom/prometheus:v3.15.0 test rules /rules/tests.yml ;;
 load-test) python3 scripts/experiments.py load ;;
 verify)
  "$0" test
  "$0" rules
  terraform -chdir=infra fmt -check; terraform -chdir=infra validate
  python3 scripts/check-manifests.py
  "$0" smoke
  python3 scripts/observability-check.py
  ;;
 teardown)
  docker compose down
  if test -f .kubeconfig && kind get clusters 2>/dev/null | grep -qx "$cluster"; then
   k get nodes >/dev/null
   kind delete cluster --name "$cluster"
   mkdir -p .runtime/old-state
   for file in infra/terraform.tfstate infra/terraform.tfstate.backup; do if test -f "$file"; then mv "$file" ".runtime/old-state/$(basename "$file").$(date +%s)"; fi; done
   rm -f .kubeconfig
  fi
  echo 'Preserved Compose volumes and .runtime/postgres. Observability ephemeral data removed with cluster.'
  ;;
 data-reset) echo 'Destructive: removes lab PostgreSQL and Redis data. Explicitly run scripts/reset-data.sh after human approval.'; exit 1 ;;
 *) echo 'Unknown lab command' >&2; exit 2 ;;
esac
