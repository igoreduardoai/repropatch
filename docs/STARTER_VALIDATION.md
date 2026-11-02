# Validação desta entrega — 27/10/2026

> Validação do kit de build inicial (starter), criado durante o hackathon e
> importado no primeiro commit em 27/10/2026. Não é código anterior ao evento.

## Executado neste ambiente

| Verificação | Resultado |
|---|---|
| `python -m pytest -q` | **42 testes passaram**. API, fila, estados, autenticação, idempotência, cancelamento, budget, paths, hashes, adapter HTTP mockado, agent loop mockado e fixtures. |
| `tsc -p web/tsconfig.json --noEmit` | Passou. |
| `tsc -p web/tsconfig.json` | Passou; JS compilado incluído. |
| Chromium + Playwright, desktop 1440×1100 | Login, criar W1, timeline, diff, três artefatos, download, criar W0 rejeitado, avaliação sem métricas inventadas e Settings com live bloqueado. |
| Chromium + Playwright, mobile 390×844 | Sem overflow horizontal da página; componentes inspecionados. |
| Erros JavaScript no teste de UI | Nenhum. |
| Scan local de padrões de segredo | Nenhum padrão suportado encontrado; não substitui revisão completa. |

A navegação HTTP local do Chromium foi bloqueada por política deste ambiente.
O teste visual usou uma ponte em memória para o FastAPI TestClient real; o
frontend compilado e as respostas da API foram exercitados, mas isso **não é
validação de rede/deploy público**. Acesso HTTP a healthz foi verificado pelo
cliente Python. O Codex precisa repetir o smoke test na URL de deploy real.

As imagens em `docs/previews/` mostram apenas a **fixture sintética roteirizada**.
Não há resultados de Muse embutidos no painel.

## O que não foi executado

- Nenhuma chamada paga à Meta e nenhum gasto de crédito.
- Nenhum reparo de issue real pelo modelo.
- Nenhum build/run de Docker (daemon indisponível neste ambiente).
- Nenhum GitHub remoto criado, commit enviado ou repositório publicado.
- Nenhum serviço de hospedagem contratado ou deploy público efetuado.
- Nenhum piloto de quatro casos, comparação de desempenho ou validação comercial.

## Estado de implementação

- UI/API/queue/fixture: implementados e testados dentro do escopo acima.
- Adapter Meta + loop: implementados e testados com mocks; usar o smoke real
  existente do usuário para conferir a integração sem pedir a chave no chat.
- Gateway de browser/repositório + live evaluator: **a implementar/integrar no Codex**.
- Execution sandbox: builder de comandos com testes; isolamento real pendente.
- Endpoint live: retorna 409 de propósito; não há fallback simulado.

## Ambiente da verificação
Python 3.13.5; Node 22.16.0; TypeScript 5.8.3; FastAPI 0.128.2;
Pydantic 2.13.5; HTTPX 0.28.1; pytest 9.0.2; Playwright 1.57.0.

`42 tests passed` significa qualidade do starter, **não 42 bugs corrigidos**.
