# PRD resumido — ReproPatch

## Promessa
Transformar vídeo de defeito + comportamento esperado em patch revisável,
acompanhado de reprodução e verificações independentes. Sem merge automático.

## Usuário e job
Operador de engenharia/QA de uma aplicação web autorizada. Quer reduzir tempo
entre um relato visual e uma correção revisável, sem aceitar falso conserto.
Validação comercial: [TBD]. Nenhum cliente/piloto comercial inventado.

## Telas entregues
1. Workbench: fila, run selecionado, pipeline, verdict e atividade.
2. Run detail: timeline, diff, artefatos, hashes e cancelamento.
3. Evaluation: W0/W1 e tabela de quatro casos ainda sem números reais.
4. Settings: modelo, status live, orçamento e limites de segurança.
5. Modal new run: relato, método e MP4 opcional autenticado.

## Visual
Aplicação de engenharia, não landing page. Navegação escura, workspace claro,
azul para ação, verde/vermelho somente para resultado de checks. Tipografia
sistema, hierarquia limpa, sem emojis. Interface em inglês; docs em português.
Dados ausentes = travessão ou [TBD], nunca 0 ou gráfico fictício.

## Fora do MVP
Qualquer-repositório/qualquer-stack, SaaS multi-tenant, SSO, cobrança, chat genérico,
clone de VS Code, marketplace, produção, pagamentos, auto-merge, reparo universal.

## Critério de entrega
Um caso real observável, reproduzível e revisável com falha correta no original,
patch final e avaliação independente. UI bonita sem esse fluxo não é produto
validado. Fixture bonita também não é prova de habilidade do modelo.
