# Checklist do demo canônico LifeGraph

## Antes da gravação

- [ ] Usar um volume Neo4j preparado e preservado para o demo.
- [ ] Confirmar `neo4j`, `gliner`, `backend` e `frontend` em execução.
- [ ] Confirmar Neo4j e GLiNER saudáveis antes de abrir a interface.
- [ ] Abrir `http://localhost:5173` e confirmar resposta HTTP 200.
- [ ] Ajustar o navegador para 100% de zoom em viewport desktop 1080p.
- [ ] Confirmar a existência da Person sintética **Reconciliation Demo**.
- [ ] Confirmar que o RefEvent importado de casamento/2019 está no LifeGraph.
- [ ] Não iniciar nem depender do REF HTTP durante a apresentação.

## Sequência esperada

- [ ] Carregar: “Nasci em 1988, casei em 2010 e me casei novamente em 2019.”
- [ ] Selecionar **Extrair narrativa** manualmente.
- [ ] Conferir três candidatos: nascimento/1988, casamento/2010 e casamento/2019.
- [ ] Selecionar **Reconciliation Demo** explicitamente em cada candidato.
- [ ] Aceitar cada candidato individualmente como declaração.
- [ ] Pausar e mostrar os três ClaimEvents como `CONVERSATION + DECLARED`.
- [ ] Reconciliar cada ClaimEvent individualmente.
- [ ] Conferir nascimento/1988 → `UNVERIFIED`.
- [ ] Conferir casamento/2010 → `DIVERGENT`.
- [ ] Conferir casamento/2019 → `CONFIRMED`.
- [ ] Mostrar razões determinísticas, RefEvent e origem ainda `CONVERSATION`.

## Segurança e replay

- [ ] Explicar que candidato da IA, declaração aceita e fato confirmado são estados distintos.
- [ ] Explicar que `UNVERIFIED` não significa falso.
- [ ] Explicar que `DIVERGENT` é relativo à evidência registral disponível.
- [ ] Não usar ações em lote ou reconciliação automática.
- [ ] Respeitar `ONE_RUN_PER_DATASET`: uma nova execução aceita cria novos claims.
- [ ] Para repetir, restaurar uma cópia limpa do volume preparado; nunca usar
      `docker compose down -v` como rotina de replay.
