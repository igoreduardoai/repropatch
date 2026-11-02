# Arquitetura de implementação

## Decisões de MVP

| Camada | Escolha | Motivo e limite |
|---|---|---|
| UI | TypeScript ES modules + CSS próprio | Entrega leve, compilável com tsc; sem framework adicional para 4 telas. |
| API | FastAPI | Contratos tipados, upload, controle de acesso e fila; nunca roda código alvo. |
| Persistência | SQLite WAL + filesystem privado | Um operador/worker. Não serve para múltiplas instâncias sem migração. |
| Worker | Processo Python separado | Jobs persistidos; chamadas e browser não bloqueiam requests. |
| IA | Meta Responses API, muse-wonder-1.0 | Confirmado pelo usuário em smoke test; adapter no servidor. |
| Browser | Playwright dentro de sandbox | Ainda a integrar no live runner. |
| Executor | Container/VM efêmero por tentativa | Sem segredos/rede/host mounts amplos; perfil por repo. |
| Avaliador | Processo separado após finalização | Nunca é ferramenta do agente; resultados não voltam ao reparo. |
| Auditor (opcional) | Muse Spark Open (pesos abertos) via Baseten | Parecer consultivo após o veredito; outro provedor/modelo; ledger próprio; nunca altera o veredito. |

## Fronteiras

1. Browser do usuário envia relatório/vídeo e escolhe case previamente aprovado.
2. API valida autorização, tamanho e idempotency key, persiste QUEUED.
3. Worker valida caso, orçamento e ambiente, prepara snapshot sem histórico futuro.
4. Vídeo é enviado à Meta somente para execução live consentida. Upload local
   sozinho não envia nada a nenhum modelo.
5. AgentLoop oferece ferramentas restritas sobre esse snapshot.
6. W1: falha correta confirmada → hash do teste → edição de fonte liberada.
7. Candidato finalizado e imutável → evaluator independente → veredito limitado
   ao conjunto de testes executados.
8. Patch, resultados, vídeo/screenshot e hashes disponíveis no painel.
9. Abertura de PR é uma extensão explícita; merge automático não existe.

## Estados
QUEUED → PREFLIGHT → REPRODUCING → FROZEN (W1) → PATCHING → VERIFYING.
Terminais: VERIFIED, REJECTED, NOT_REPRODUCED, BLOCKED, BUDGET_EXCEEDED,
CANCELLED, ERROR. Um crash em progresso vira ERROR na retomada, sem nova cobrança.

VERIFIED significa “passou nos checks executados”, nunca “livre de qualquer bug”.
W0 pode escrever e executar testes, mas não é forçado a congelá-los.

## Dados e contratos
- runs: ID, caso/commit, método, modo, timestamps, status, payload e resultado.
- events: append-only no caminho normal; at, stage, kind, mensagem curta, evidência.
- artifacts: tipo, nome, hash, tamanho, run_id e path privado.
- spend: reservation por request, consumo consolidado, UNKNOWN em timeout.
- case manifest: commit inicial, setup/test commands revisados, licença, origem de
  vídeo, referências de gabarito mantidas fora do agente e versão do protocolo.

## API implementada
GET /healthz (sem segredo)
GET /api/config, /api/budget, /api/evaluation
GET /api/runs; POST /api/runs (Idempotency-Key)
GET /api/runs/{id}; GET /api/runs/{id}/events?after=N
POST /api/runs/{id}/cancel
GET /api/runs/{id}/artifacts/{artifact_id}
POST /api/videos (MP4, 50 MiB; assinatura mínima, ffprobe isolado necessário no live)

Todas as rotas /api exigem Bearer token. Sem CORS amplo: deploy na mesma origem.
Estado atual: somente case pagination-fixture. Live cria 409 por segurança.

## Budget
Persistir reserva do input contado (com buffer) + output máximo, sem cache.
Somar output_tokens uma vez; reasoning_tokens é parte dele. Usar uso real e
cache real para conciliação. Não executar ferramentas hospedadas no loop do MVP.
A contagem de contexto não é garantia de faturamento; ver Sources. Divergência,
timeout ou usage ausente → parar; operador concilia antes de liberar.

## Evolução após primeiro caso real
Postgres + queue distribuída + S3 podem substituir SQLite/fs para escalabilidade.
Isso não é necessário para o primeiro piloto. VM ou sandbox gerenciado deve
substituir Docker básico antes de atender repositórios hostis de terceiros.
