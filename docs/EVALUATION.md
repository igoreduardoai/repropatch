# Piloto aprovado: 4 casos × 2 métodos

W0 = Muse Wonder competente: reproduza, corrija e teste. Sem restrição artificial
que o impeça de criar testes ou verificar regressões.
W1 = mesmo Wonder com a exigência do protocolo: confirmar falha correta antes de
editar, congelar reprodução, reparar e executar checks públicos sem enfraquecê-la.

## Igualdade de condições
Mesmo commit inicial, vídeo, comportamento esperado, tools, rede permitida,
contexto, orçamento máximo e contadores. Sessões independentes. Ordem alternada
W0/W1, registrada antes. Não comparar Muse Code num braço e API no outro.

## Origem dos casos
Casos reais com licença e ambiente reproduzível. SWE-bench Multimodal é uma
possível fonte, mas disponibilidade de 4 MP4 NÃO é confirmada. Não fabricar
links. Reprodução própria em vídeo deve ser rotulada como tal.

## Separação de respostas
T0 setup: operador confirma falha no original e pass com patch de referência.
T1 agente: nunca recebe patch/test_patch/hidden_eval/hints reveladores/histórico
posterior. Pode ver testes públicos existentes no commit inicial.
T2 freeze: snapshot final do patch e declaração de conclusão/abstenção.
T3 evaluator: aplica testes do mantenedor fora do agente. Resultado não volta
para nova tentativa. O produto real não promete acesso aos testes secretos de
qualquer cliente; eles são instrumento deste benchmark.

## Métricas
- fixed: testes independentes relevantes passam, sem regressões no conjunto.
- false_success: claim=resolved mas avaliação independente reprova.
- abstained: candidato não entregue ou incapacidade declarada; não conta como fix.
- not_reproduced vs infrastructure_error: denominadores e motivos separados.
- all attempts, model calls, billed input/output/cache, USD, time, interventions.
- Fixes por caso, não só acurácia de mensagens. Bloquear tudo não é vitória.

## Freeze antes de inferir
Case IDs, commit SHAs, vídeos/hashes, versões de tools, parâmetros e lista de
checks independentes precisam estar registrados antes. Não escolher casos após
ver os acertos. Alteração de protocolo após primeiro par = rodada de desenvolvimento
separada, nunca mesclar silenciosamente no resultado final.

## Interpretação
Quatro casos mostram viabilidade e sinal inicial. Não estimar probabilidade de
vencer hackathon. Empate significa ausência de vantagem observada, não equivalência
comprovada. Fixtures e mocks ficam fora de todos os denominadores reais.

## Primeiro marco
Um caso executável, duas tentativas comparáveis, dois patches e um avaliador
independente. Só depois ampliar ou gastar em interface adicional.

## Auditor consultivo (Muse Spark Open, pesos abertos) — adicionado depois do piloto
Não faz parte do protocolo pré-registrado W0/W1 e não altera nenhuma métrica acima.
Depois do veredito final, `repropatch/auditor.py` envia diff + teste congelado +
resultado do avaliador para `meta-models/muse-spark-open-1026` (Baseten, API
compatível com OpenAI). Saída: escopo, risco de overfitting, regressões prováveis,
accept/review, confiança. Regras: opt-in, sem chave = DISABLED rotulado, sem retry
em 429/5xx, ledger próprio (teto US$3), custo estimado pelo preço de lista público
do Baseten (não é fatura), o parecer nunca volta ao agente de reparo e nunca muda
VERIFIED/REJECTED.

Medido (27/10/2026, `docs/evidence/auditor/`):
- van-389 W0 (patch real, hash conferido com pilot-results.json): accept, risco baixo.
- Controle sintético (patch overfit escrito à mão, nunca executado): review, risco alto.
  O controle contém um comentário revelador ("make the reported case pass"); é um
  teste fácil, não uma medida de sensibilidade.
- Os outros três patches VERIFIED (389 W1, 401 W0/W1) não foram exportados para este
  repositório; ficam em `.data/` privado e não foram auditados aqui. As quatro
  abstenções não têm patch final; o auditor não foi usado para inventar explicações
  sem os traces.
Interpretação: demonstra integração e um sinal qualitativo. Não mede acurácia do
auditor nem prova superioridade de nenhum método.
