# Roteiro de vídeo — demo canônico LifeGraph

Tempo estimado: 2–3 minutos (aproximadamente 320 palavras).

## Narração e ações

**[Abertura — 0:00]**

O LifeGraph investiga como narrativas pessoais podem ser organizadas em um grafo
temporal sem confundir o que uma inteligência artificial extrai com o que foi
declarado por uma pessoa ou confirmado por uma fonte registral. A regra central
é simples: candidato da IA não é declaração aceita, e declaração aceita não é
fato confirmado.

**[Narrativa e extração — 0:20]**

Vou carregar a narrativa canônica: “Nasci em 1988, casei em 2010 e me casei
novamente em 2019”. O botão apenas preenche o texto. A extração só começa quando
eu seleciono “Extrair narrativa” e não grava nada no grafo.

O pipeline identifica três candidatos: um nascimento e dois casamentos. Cada
card mostra evento, sujeito, data e o motivo determinístico da associação. Esses
resultados continuam sendo candidatos temporários da IA.

**[Revisão e aceitação — 0:55]**

Agora reviso cada candidato e escolho explicitamente a pessoa “Reconciliation
Demo”. Nenhuma pessoa é selecionada automaticamente. Aceito cada item
individualmente usando “Aceitar como declaração”. Neste momento surgem três
ClaimEvents no grafo, todos com origem CONVERSATION e status DECLARED. Isso
registra uma declaração revisada, não confirma um fato e não consulta o REF.

**[Reconciliação — 1:30]**

Seleciono cada declaração no grafo e aciono, separadamente, “Reconciliar com
evidência registral”. A comparação determinística usa apenas RefEvents já
importados para a mesma pessoa e o mesmo tipo de evento.

O nascimento de 1988 fica UNVERIFIED: a evidência é insuficiente, o que não
significa que a declaração seja falsa. O casamento de 2010 fica DIVERGENT: ele
diverge da evidência atualmente disponível, sem afirmar que a pessoa só poderia
ter um casamento. O casamento de 2019 fica CONFIRMED e exibe a evidência
registral compatível.

**[Encerramento — 2:15]**

Em todos os casos, a origem continua CONVERSATION. O que muda é apenas o estado
de verificação. Assim, o LifeGraph torna visíveis a revisão humana, a proveniência
e os limites da evidência, sem transformar automaticamente uma inferência da IA
em fato.
