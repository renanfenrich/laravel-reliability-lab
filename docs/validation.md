# G1 validation report
Local goal complete; READY FOR HUMAN REVIEW. PASS means the stated check, not production reliability or monthly compliance. Final operating code commit8dcfaca; later documentation/evidence commits do not change deployed application behavior.

| Check | Actual result | Evidence |
|---|---|---|
| Host tools/Docker/resources/ports/contexts | PASS; pinned kind0.30.0/Terraform1.16.5/local kubectl1.34.0; no default-context mutation | doctor.log, cluster-up.log |
| Pinned app/simulator builds | PASS; private infra/.env excluded from final image | build-final.log, build-scheduler-stderr.log, image-context-check.log, safety-verified.log |
| Application reliability tests | PASS13 tests/47 assertions, PostgreSQL18/Redis8.2; separate committed test DB | tests-scheduler-stderr.log, verify-recreation.log |
| Auth/validation/idempotency/durable queue-window/retries/duplicate/stale fencing/deadlines | PASS meaningful scenarios, subsecond deadline and content-length regression included | tests/Feature/ReportsTest.php and test logs |
| Rule mathematics/alerts | PASS9 short +3 intended30-day simulated fixtures; failures/latency/unfinished/missing/zero/recovery | rules-final.log, verify-recreation.log, observability/tests*.yml |
| Terraform init/fmt/validate | PASS; validation also with absent kubeconfig in isolated CI copy | terraform-final.log, ci-terraform-validation.log |
| CI Terraform image pin | PASS image executes1.16.5 | ci-terraform-image-version.log |
| Kubernetes schema/server validation | PASS41/41 strict schema1.34, no skips; server dry-run only | kubeconform-final.log, manifest-server-validation.log |
| Dedicated bootstrap/deploy/redeploy | PASS; Terraform owns deployment objects, kind cluster only | deploy-recreation.log, cluster-recreation.log |
| Full Kubernetes journey | PASS8 concurrent idempotent submissions, one completed DB result | smoke.json, verify-recreation.log |
| Metrics/logs/Grafana | PASS exporter/KSM/cAdvisor targets, correlated exact report query,15 provisioned panels | observability.json, verify-recreation.log |
| Fault experiments/alert recovery | PASS healthy/external delay/exhaustion/SIGKILL and accelerated alert fired/resolved | experiments.json, worker-final.json |
| Capacity | Measured40-rps passing burst/50-rps latency breach; all accepted deadline cohorts counted | capacity-retake.json, capacity-50.json, docs/capacity.md |
| Teardown/data retention/recreation | PASS5221 prior records retained,5227 at after-check, old checksum survives | retention-before.json, retention-after.json, teardown.log |
| Actual credential values absent from Git candidates | PASS; ignored credential/state files remain private | secret-check.log, safety-verified.log |

## Failed/invalid observations retained
Initial PHP8.4.13 DOM compilation, Closure middleware, missing Mockery/test env precedence, Terraform empty volumes/empty storageClass/restart annotations, PostgreSQL volume privileges, Alloy River syntax and promtool sample-limit/float comparisons failed before fixes. Corresponding evidence logs/diagnostic excerpts and Git history are retained; the first compiler output was truncated, so initial-build-failure.txt explicitly preserves only the observed excerpt. Some early command logs lack exact start/end wrapper timestamps; no durations were invented.

Initial pod deletion left attempts1, INVALID for interruption proof. Second source run exposed second-resolution timestamps and client EOF framing. Pre-framing capacity and original60-rps/128-thread capacity were INVALID;512-thread60-rps retake still sender-limited (868ms lateness,7.33% client errors). Refined50-rps test sent accurately (1.28ms lateness) and breached latency with no HTTP errors; failures/timeouts remain raw. A scheduler JSON/console framing assertion failed before separate stderr routing; final exact-query log check passed. Pre-framing fault polling was tagged normal; that normal HTTP interval is unsuitable for compliance claims. No data reset or metric deletion was used to clear an alert.

## Unexecuted/unestablished
Hosted GitHub Actions (definition only, no remote/push), actual rolling30-day attainment, production experience/sizing/HA, cloud/AWS, sustained/load-balanced/multi-region tests, backups/full disaster recovery, external notification delivery, full browser/accessibility QA and destructive data-reset. These are explicit scope/measurement limits; not silently counted as passes. Pure simulator does not prove exactly-once mutating downstream effects. Server middleware metrics omit pre-middleware admission/bootstrap/client-network delay; client experiment timings expose this gap. Persistent PostgreSQL retention is not a backup proof; ephemeral telemetry history is lost on cluster deletion.

Command timestamps/durations/exit codes/SHA: evidence/commands.jsonl. Source/config/deployed-image versions: versions-current.json and composer.lock. Final reports: docs/incident.md and docs/capacity.md.

## Grafana panel regression repair
The user subsequently found panel errors. Original validation counted provisioned panels but did not exercise datasource plugins. Grafana startup auto-update removed registered Prometheus/Loki plugins and failed against read-only bundled files. Disable preinstallation and auto-update so exact image-bundled plugins remain loaded; read-only root stays enabled. `grafana-regression-before.log` records HTTP404; `grafana-regression-after.log` and `observability.json` record both healthy datasources and15 successful panel queries with nonempty report-state, resource and log frames. Earlier observability evidence is preserved as `observability-before-grafana-fix.json`.

## Infraestrutura e nova carga (2026-10-11)
Coletor host: teste de unidades e filtragem DockerPASS. Dashboard novo40 painéis; consultas dos55 painéis nos dois dashboardsPASS comframes,5targetsUP; smokePASS;12 fixtures de regrasPASS; Terraformfmt/validate, manifestsdeterminísticos e segurançaPASS. ConfiguraçãoPrometheus validada pelo promtool no pod com credenciais Kubernetes. Tentativas externas de checkconfig falharam por montagem de rules/serviceaccount ausentes e não indicavam configuração validada. Consulta de erros de rede inicialmente falhou por colisão de labels e foi corrigida. Evidência em evidence/infrastructure-20261011 e observability.json. Browser mostrou gráficos atuais. Longo soak/overhead do coletor não medidos; hostedCI não executado.
Carga separada em evidence/load-20261011T175620Z:2640requests,40req/s último ponto aprovado;50req/s saturação de latência com p9913.97s e zeroerrosHTTP,100%deadline. Esta execução terminou antes da instalação do coletor host; não existe retrospectiva de métricas host para essa carga.

## Alertas/e-mail local (2026-10-11)
PASS:13fixtures promtool (10curtas +3janelas30dias simuladas), cobertura positiva das12 regras de burn, ausência de telemetria/zero tráfego/recuperação e novo targetdown. PASS amtoolconfig e promtoolconfig nos pods. Terraformfmt/validate e manifestsdeterminísticos com46objetos; segurança de credenciaisPASS. Novos containers fixados Alertmanager0.34.1/Mailpit1.31.5. Não há prova de observação real de30dias.

PASS em evidence/email-5fdb4d90db:15injeções explicitamente notification-fixture exercitaram todasrotas firing/resolved;3condições Prometheus reais dispararam e resolveram (falha terminalfault, scheduler semheartbeat, coleta host parada),36e-mails locais recebidos/exportados. Alertas de burn SLO foram testados porfixtures matemáticos e de envio; não confundir com disparo ao vivo. Scheduler/coletor restaurados, relatório terminalfailed mantido. PASS smoke e observabilidade pós-recuperação:7targets, regras saudáveis, Alertmanager ativo, APIcaixa401semcredencial/200comcredencial,55consultasGrafana. Commands.md/logs registram baseSHA e alterações emworkingtree; configuração final é preservada no commit desta funcionalidade.

Não executados: entrega externa, browser visual da caixa (cliente in-app bloqueou acesso), hostedCI, persistência/HA da caixa. Mailpit/AlertmanageremptyDir são efêmeros; JSONexportado é evidência durável. CaixaLAN http://192.168.1.9:18025 autenticada lab/LAB_TOKEN. O experimento ao vivo foi de6min26s, separado das janelas SLO.
