# Fontes e classificação

## Contexto fornecido / aprovado (não reexecutado aqui)
- Projeto: ReproPatch, Indie / Push the Frontier; inferência online.
- Smoke test relatado pelo usuário: muse-wonder-1.0 com ferramentas/imagem/vídeo,
  custo US$0,014; clipe de 3 s sintético, quase parado. Não generalizar tokens/s.
- Orçamento aprovado no escopo da conversa: piloto incremental até US$24,
  quatro casos × dois métodos; teto US$3 por execução.
- Fluxo e comparação: COMPARACAO-META-v2 colada no chat, linhas 171–195, com
  correções posteriores: baseline competente, mesmo runner, oráculo pós-finalização,
  não aprovar ocultamente modelo/simulador a partir de dados inventados.

## Documentação primária consultada em 27/10/2026
- Meta quickstart: https://dev.meta.ai/docs/quickstart
  Base URL https://api.meta.ai/v1, API key server-side.
- Meta video: https://dev.meta.ai/docs/video-understanding
  Files API purpose=user_data; input_file com file_id. O exemplo documentado usa
  Spark; Wonder com vídeo foi validado pelo usuário, não por este pacote.
- Tool calling: https://dev.meta.ai/docs/tool-calling
  Function tool schema, function_call e function_call_output.
- Token counting: https://dev.meta.ai/docs/token-counting
  POST /v1/responses/input_tokens; contagem de contexto != fatura, especialmente
  em tools hospedadas. reasoning_tokens é subconjunto do output total.
- Pricing: https://dev.meta.ai/docs/pricing-rate-limits
  Configuração inicial Wonder: input $4/M; output $20/M; cached input $0.20/M.
  Conferir novamente antes do piloto; não assumir cache.
- Codex AGENTS.md: https://developers.openai.com/codex/guides/agents-md/
  Instruções persistentes do projeto.
- Docker isolation: https://docs.docker.com/engine/security/userns-remap/
  Preferir execução sem root e compreender limites de isolamento.

## Decisões propostas nesta entrega, não regras oficiais
- Front TypeScript nativo, FastAPI, SQLite WAL e single worker.
- Repo começa privado; publicação posterior para submissão após revisão.
- Autenticação de operador, limite de upload 50 MiB, sandbox/rede bloqueados.
- UI inglesa. Sem obrigação de usar React/Next, múltiplos modelos ou SAM.
- Gate live permanece fechado até testes de isolamento/reprodução reais.

## Evidência produzida aqui
Ver VALIDATION.md. Testes de infraestrutura e fixture não são modelo Meta,
benchmark de mercado, validação comercial ou probabilidade de vitória.
