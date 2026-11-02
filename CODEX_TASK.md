# CODEX TASK — implementar e subir ReproPatch

## Decisão fechada
ReproPatch aprovado. Execute; não proponha novas ideias nem novos rankings.
O usuário quer repositório, front-end, backend, arquitetura, teste e deploy.
Este pacote contém uma base funcional; não é só um prompt ou wireframe.

## Contexto já confirmado pelo usuário
- Meta Global AI Developer Hackathon, Indie / Push the Frontier.
- Muse Wonder `muse-wonder-1.0` já respondeu a texto, ferramentas, imagem e vídeo.
- Smoke test relatado: US$0,014. Não foi executado por este pacote.
- Inferência online autorizada; não há exigência de rodar modelo no Mac.
- Piloto aprovado: quatro casos reais × W0/W1; orçamento incremental até US$24,
  no máximo US$3 por execução. Sem contratação adicional de infraestrutura paga.
- A chave já existe no ambiente seguro do usuário/runner original. Procure somente
  nas variáveis indicadas ou peça que seja inserida no secret manager, nunca no chat.
- O app promete patch verificável, NÃO correção garantida de qualquer software.

## Primeiro: rodar a base entregue
1. Leia AGENTS.md e VALIDATION.md.
2. Execute setup local, suíte pytest, typecheck/build e inspecione a UI.
3. Execute as fixtures W0/W1; confirme que W0 é rejeitado por regressão e W1 passa
   nos checks executados. Isso não pode entrar no benchmark real.
4. Crie `repropatch` privado na conta GitHub verificada; não vincule outras identidades.
   Use o script fornecido. Se o nome já existir, inspecione antes; não sobrescreva.
5. Registre o primeiro commit honesto. Nunca altere datas para satisfazer o evento.

## Entrega P0 — um caso real ponta a ponta
Objetivo: um vídeo real de bug + commit anterior → reprodução → teste congelado
→ patch → avaliação independente. Sem dashboard extra antes disso.

### Caso e ambiente
- Selecione um repositório JS/TS pequeno, licenciado, com issue real, vídeo acessível
  e teste de referência. Não invente quatro URLs para preencher o formulário.
- Faça uma lista determinística dos candidatos e registre inclusões/exclusões
  ANTES das chamadas; não escolha somente bugs que o agente já resolveu.
- Caso não haja vídeo original, grave a reprodução do bug público, identifique
  como reprodução própria e não o atribua ao SWE-bench original.
- Prebuild da imagem com dependências resolvidas e fixadas, sem chave Meta.
- Confirme que o teste independente falha no commit inicial e passa no patch de
  referência. Só então esse caso entra no piloto.
- Clone/fetch acontece na preparação controlada, não numa ferramenta livre do agente.
  Crie snapshot sem histórico posterior, solution patches ou metadados que revelem a resposta.

### Ferramentas do agente
Implemente um Gateway compatível com `repropatch/agent.py`:
- list_files/read_file: escopo permitido, limites e redação de segredos;
- browser_observe/browser_action: Playwright no sandbox, screenshots e ações reais;
- write_reproduction_test/run_reproduction: teste dentro do sandbox;
- freeze_reproduction: validação do motivo da falha, baseline + hash fora do workspace;
- write_source/apply_patch: apenas arquivos permitidos; respeitar congelamento W1;
- run_public_regressions: nunca inclui oracle/hidden tests;
- submit_candidate: snapshot de patch e claim; encerra ferramentas do agente.

O modelo não escolhe host shell. Comandos de build/test devem vir de perfil de
caso revisado, não de string livre executada na API.

### Regras de reprodução
Um teste que falha por import quebrado, timeout, erro de sintaxe ou setup não
passa pelo gate. A primeira implementação pode exigir revisão explícita do
operador para confirmar o motivo correto; contabilize essa intervenção no piloto.
Faça também a verificação de sensibilidade do teste ao comportamento esperado.
Congelar hash não prova que o teste é semanticamente bom.

### Avaliação pós-reparo
Depois de submit_candidate, o evaluator recebe um snapshot do candidato. Ele
executa reprodução congelada + regressões e, no benchmark, testes do mantenedor
mantidos fora do workspace. Não devolva resultados ocultos para mais tentativas.
Sem patch da solução, answer key, futuro git log ou acesso web à PR corretiva.

### Integração UI/API/worker
- Troque o hard gate live 409 apenas quando o caminho real estiver integrado e
  os testes de isolamento passarem. Não basta mudar REPROPATCH_ENABLE_LIVE=true.
- Acrescente cadastro de case aprovado por manifesto; não aceite qualquer URL
  da internet, paths do host ou comandos enviados pelo browser.
- A UI já possui timeline, diff, artifacts, upload, histórico e painel W0/W1.
  Alimente com eventos reais; não reutilize os resultados da fixture.
- Manter motivo de falha, custos, timestamps e IDs de resposta sem exibir chain of thought.

## Entrega P1 — piloto de quatro casos
- W0: instrução competente para reproduzir, corrigir e testar. Pode criar testes.
- W1: mesma entrada, modelo, ferramentas e budget, com o protocolo obrigatório.
- Não usar Muse Code em um braço e a API no outro.
- Contrabalancear ordem W0/W1; sessões independentes, sem compartilhar memória,
  patch anterior, resultado oculto ou cache de conteúdo com resposta corretiva.
- Execute primeiro um par para confirmar infraestrutura. Se mudar o protocolo
  depois, identifique como desenvolvimento e não misture resultados incompatíveis.
- Registre todas as tentativas, inclusive abstenção e timeout. Não rerode até passar.
- Uma igualdade em 4 casos é ausência de vantagem observada, não equivalência provada.
- Dashboard mostra n, corrigidos, falsos sucessos, regressões, abstenções, custo,
  duração e intervenções humanas. Nada de chance de vencer inferida desse piloto.

## Entrega P2 — deploy
- Primeiro deploy privado/autenticado, mesma origem, um API process + um worker.
- Não hospedar long-running agent/browser no request de função serverless.
- Usar VM/container host com armazenamento persistente ou adaptar para Postgres
  e object storage se o provedor não oferecer disco persistente.
- Worker de código desconhecido deve ficar em host/serviço isolado; API pública
  não recebe docker.sock. Docker simples do starter não é garantia multi-tenant.
- Provedores pagos não aprovados: preparar config e pedir somente essa decisão.
- Não abrir endpoint live anônimo. Para jurados, separar replay público sanitizado
  da execução paga de operador. Não afirmar que replay é inferência ao vivo.

## Critérios de aceite
- UI desktop e mobile sem overflow e com estados vazio/carregando/erro.
- Autenticação, idempotência, cancelamento e recuperação de worker testados.
- Um caso real com evidências completas, não só mock ou fixture.
- Teste congelado não pode ser editado nem suprimido para aprovar um reparo.
- Segredos e evaluator invisíveis ao código alvo/agente.
- Reservas de budget e consumo real registrados; stop em incerteza.
- README, LICENSE/NOTICE de dependências, prior work e limites corretos.
- URLs, commits e resultados reais no relatório final; status live declarado.

## Não fazer
Não reconstruir tudo por preferência de framework. Não criar login social,
billing, multi-tenancy, marketing landing, marketplace ou 5 agentes decorativos.
Não apresentar os testes sintéticos como vantagem medida da Meta.
Não fazer auto-merge. Não publicar segredos ou código de clientes.

## Handoff final obrigatório
Responda com: repo e visibilidade; URL de deploy e modo; commit SHA; testes
executados; um exemplo real com patch+hashes; gasto API real; tabela W0/W1; o que
continua pendente. Não diga que subiu algo sem verificar a URL e a execução.
