# Segurança — modelo de ameaças e limites

## Não confiar
Repositório, scripts de instalação, vídeo, páginas, logs e instruções em arquivos
podem ser maliciosos. A permissão para consertar um repo não autoriza acesso à
máquina pessoal, chave API, produção ou referências de solução.

## Controles entregues
- Bearer token obrigatório em /api; chave Meta exclusivamente backend.
- Path traversal e symlinks rejeitados; .git/.env/hidden/evaluation inacessíveis
  ao Workspace helper; writes permitidos somente em src/ no perfil básico.
- Hash externo do teste, bloqueio de escrita antes de freeze em W1.
- SQLite claim atômico, idempotency key e status terminal explícito.
- Docker command builder: no network, read-only root/source, non-root,
  no-new-privileges, cap-drop, memory/cpu/PID/time limits, sem socket/segredo.
- Templates de geração rejeitados se vierem de fixture não proprietária.

## Limites conhecidos
- Docker CLI disponível e isolamento real NÃO foram testados neste ambiente.
- Rodar Docker em host compartilhado não é segurança suficiente para SaaS
  multi-tenant de execução de código desconhecido. Preferir VM efêmera/dedicada.
- Signature MP4 não valida duração/codecs; executar ffprobe isolado antes do live.
- O starter não tem quotas de armazenamento, antivírus ou rate limiting de upload.
  Adicionar quotas e limites no proxy antes de expor na internet.
- Existe uma credencial de operador, não RBAC/multi-tenant. Sem OAuth implementado.
- Freeze/hash só protegem a integridade dos bytes; não provam semântica de teste.
- Testes ocultos podem vazar via histórico Git ou internet. Bloquear ambos; só
  retirar um arquivo .spec não isola respostas.
- Patch pode alterar infra de build/test e mentir sobre resultados. Usar perfil
  de arquivos editáveis, evaluator externo e inspeção de diff.
- Logs de modelo podem conter dados do usuário; manter privados, redigir secrets
  e não exibir raciocínio privado. Publicar apenas trace de ações e evidências.
- Uso medido pela conta Meta é autoridade financeira; o ledger é um controle
  da aplicação e não conhece outros clientes da mesma chave.

## Antes de liberar live/public
Validar isolamento em teste de fuga controlado, set de permissões, limits,
cleanup, reviewer humano de repro, TLS, quotas, autenticação e firewall.
Nunca usar a UI pública para rodar código arbitrário sem esses controles.

## Live sandbox (repropatch/docker_runtime.py, gateway.py)
Implemented and exercised against a stock node image in tests/test_docker_live.py: network none, read-only rootfs,
tmpfs workspace, cap-drop ALL, no-new-privileges, uid 65534, no host mounts/env/socket, labelled containers swept on
worker start, per-run cleanup. NOT exercised: Chromium/Playwright (needs the operator image) and hostile-escape tests.
See docs/CASE_REGISTRY.md for the registry, acceptance and image contract.
