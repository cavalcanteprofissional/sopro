# 04 — Roadmap de implementação (free tier)

Estimativas em semanas de trabalho parcial; ajuste conforme sua disponibilidade. Cada fase termina com uma **definição de pronto (DoD)** verificável.

## Fase 0 — Validação (1 semana)

**Objetivo:** provar que o conceito funciona antes de construir.

- Montar glossário seed com ~200 termos de tecnologia (ver `07-glossario-seed-modelo.md`).
- Gravar 3 aulas/vídeos de ~10 min em inglês (IA/tecnologia) e **anotar manualmente** os termos falados com marcação de tempo (conjunto de referência).
- Transcrever com Whisper local e medir quantos termos do glossário aparecem corretos no texto.
- Escolher a máquina de referência (CPU, RAM) para as metas de desempenho.

**DoD:** planilha com taxa de acerto dos termos na transcrição; decisão sobre modelo inicial.

## Fase 1 — Pipeline em linha de comando (2 semanas)

- Captura de loopback e microfone no Windows com etiquetas de fonte.
- VAD + segmentação.
- `STTProvider` local funcionando com dica de vocabulário.
- Matcher básico (n-gramas + aliases) imprimindo termos no terminal com marcação de tempo.
- Modo benchmark: processa arquivo de áudio e compara com a anotação.

**DoD:** recall e precisão medidos no conjunto da Fase 0; latência por etapa registrada.

## Fase 2 — Overlay e persistência (2 semanas)

- Pop-up conforme especificação (sem foco, sempre no topo, fila, cooldown).
- SQLite com esquema e migrações; histórico por sessão.
- Tela mínima de configurações (fontes, idioma de saída, duração, posição).
- Ícone na bandeja e atalhos globais.

**DoD:** 30 min de uso em chamada real sem roubar foco; histórico exporta em CSV.

## Fase 3 — RAG e desambiguação (2–3 semanas)

- Embeddings locais e índice vetorial das acepções.
- `SenseResolver` em cascata (acepção única → domínio → vetor → LLM).
- Caminho de termo fora do glossário com LLM local, cache e aprovação pelo usuário.
- Provedor Groq opcional (STT e LLM) com aviso de privacidade e tratamento de limites.

**DoD:** em termos ambíguos do conjunto de teste, a acepção correta é escolhida em ≥ 85% dos casos (meta a calibrar); queda de rede não derruba o app.

## Fase 4 — Empacotamento e experiência (1–2 semanas)

- Instalador para Windows; modelos baixados no primeiro uso com barra de progresso.
- Primeira execução: aviso de consentimento, escolha de domínio e idioma.
- Tratamento de erros amigável; logs sem conteúdo de fala.
- Tela de gerenciamento de glossários (importar/exportar).

**DoD:** instalação em máquina limpa sem dependências manuais; checklist de aceite do `01` cumprido.

## Fase 5 — Escala e portabilidade (contínua)

- Pacotes de domínio adicionais (direito, saúde, finanças) com curadoria e licenças claras.
- Camadas de plataforma para Linux e macOS.
- Avaliar versão mobile (microfone) reutilizando o núcleo.
- Feedback de usuário: botão "irrelevante" alimentando a lista de exclusão.

## Métricas de acompanhamento

| Métrica | Como medir | Meta inicial |
|---|---|---|
| Latência fim-da-fala → pop-up (P95) | Timestamps por etapa | ≤ 3 s |
| Recall de termos | Conjunto anotado | ≥ 85% |
| Precisão | Conjunto anotado + marcação "irrelevante" | ≥ 90% |
| Pop-ups falsos/min | Contagem em sessões reais | ≤ 2 |
| CPU/RAM | Monitor do SO na máquina de referência | ≤ 30% / ≤ 2 GB |
| Acerto de acepção | Casos ambíguos anotados | ≥ 85% |

## Conjunto de teste (especificação)

- 3 a 5 áudios de 10 min, sotaques variados, temas diferentes dentro de tecnologia.
- Anotação em CSV: `inicio_s, fim_s, termo_canonico, acepcao_esperada`.
- Reservar um áudio **somente para validação final** (não ajustar regras nele).

## Riscos e mitigação

| Risco | Prob. | Impacto | Mitigação |
|---|---|---|---|
| STT erra termos técnicos | Alta | Alto | Dica de vocabulário, aliases fonéticos, modelo maior se a CPU permitir |
| Excesso de pop-ups | Média | Alto | Cooldown, orçamento/min, lista de exclusão, feedback do usuário |
| Latência alta em CPU fraca | Média | Alto | Modelo menor, quantização, opção Groq |
| Free tier muda ou limita | Média | Médio | Local como padrão, camada de provedores |
| Captura de áudio varia por SO | Média | Médio | Isolar em camada de plataforma |
| Consentimento/LGPD em calls | Média | Alto | Aviso inicial, sem gravação de áudio, sem contexto por padrão |
| Licença de glossários externos | Média | Médio | Curadoria própria, registrar licença por pacote |
| Instalador grande | Média | Médio | Modelos sob demanda, componentes opcionais |
| Pop-up rouba foco em reuniões | Baixa | Alto | Flags de janela sem ativação e teste dedicado |

## Marcos

1. **M0** conceito validado (fim da Fase 0).
2. **M1** pipeline medido (Fase 1).
3. **M2** protótipo usável em aula real (Fase 2).
4. **M3** pop-ups com acepção contextual (Fase 3).
5. **M4** versão instalável 0.1 (Fase 4).
