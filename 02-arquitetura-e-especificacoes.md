# 02 — Arquitetura e especificações

## 1. Visão geral do pipeline

```
[Fonte de áudio: loopback | microfone]
        │  PCM 16 kHz mono, frames de 20–30 ms
        ▼
[VAD] ──► segmentos de fala (com sobreposição curta)
        ▼
[STTProvider]  LocalWhisper (padrão)  |  GroqWhisper (opcional)
        ▼
[Normalizador de texto]  minúsculas, pontuação, números, hifens
        ▼
[TermMatcher]  busca no glossário do(s) domínio(s) ativo(s)
   ├─ achou termo conhecido ──► [SenseResolver] ──► [PopupManager]
   └─ candidato desconhecido ─► [RAG + LLM] ─► cache ─► [PopupManager]
        ▼
[Repository SQLite]  detecções, histórico, cache, configurações
```

Princípio central: **o LLM não participa de toda frase.** O caminho rápido é busca em dicionário local; RAG/LLM só resolve ambiguidade ou termos fora do glossário. Isso reduz latência, uso de CPU e consumo de free tier.

## 2. Módulos e responsabilidades

| Módulo | Responsabilidade | Depende de |
|---|---|---|
| `audio` | Abrir fontes, entregar frames PCM etiquetados | SO (camada de plataforma) |
| `vad` | Detectar início/fim de fala, formar segmentos | `audio` |
| `stt` | Interface `STTProvider` + implementações local e Groq | `vad` |
| `text` | Normalização e tokenização | `stt` |
| `matcher` | Detectar termos (n-gramas, aliases, lematização leve) | `text`, `glossary` |
| `glossary` | Carregar/gerenciar pacotes de domínio | SQLite |
| `rag` | Embeddings, busca vetorial, escolha de acepção | `glossary` |
| `llm` | Interface `LLMProvider` (local/Groq) para exceções | `rag` |
| `popup` | Fila, regras de exibição, renderização | UI |
| `repo` | Acesso a dados (SQLite) | — |
| `config` | Preferências, perfis, chaves (armazenadas localmente) | — |
| `app` | Orquestração, bandeja, atalhos, ciclo de vida | todos |

**Regra de arquitetura:** `matcher`, `glossary`, `rag`, `llm`, `repo`, `config` formam o **núcleo** (sem dependência de SO ou UI). `audio` e `popup` são **camadas de plataforma**. Isso viabiliza portar para outros SO e mobile sem reescrever o núcleo.

## 3. Interfaces (contratos)

### 3.1 `STTProvider`
- Entrada: bytes PCM 16 kHz mono, etiqueta da fonte, dica de vocabulário (lista de termos), idioma (`en`).
- Saída: `{text, start_ms, end_ms, confidence?, source}`.
- Operações: `warmup()`, `transcribe(segment)`, `close()`.
- Erros esperados: indisponibilidade, limite de taxa, timeout. O orquestrador deve alternar para o provedor local ou pausar com aviso (RNF-10).

### 3.2 `LLMProvider`
- Entrada: prompt de sistema + contexto estruturado.
- Saída: **JSON válido** conforme esquema da seção 6 (ver prompts em `05-prompts.md`).
- Implementações: local (via servidor local compatível com API de chat) e Groq.

### 3.3 `Matcher`
- Entrada: texto normalizado + janela de contexto.
- Saída: lista de `{term_id, surface, start_idx, end_idx, ambiguity_flag}`.

### 3.4 `SenseResolver`
- Entrada: `term_id`, contexto (últimos N segundos), acepções candidatas.
- Saída: `{sense_id, score, method}` onde `method ∈ {single_sense, domain_tag, vector, llm}`.
- Estratégia em cascata: acepção única → etiqueta de domínio → similaridade vetorial → LLM (só se a pontuação ficar abaixo do limiar).

## 4. Detecção de termos (especificação)

1. Normalizar: minúsculas, remover pontuação, separar hifens, manter siglas.
2. Gerar n-gramas de 1 a 4 tokens e buscar **o maior casamento primeiro**.
3. Casar contra: forma canônica + aliases + flexões comuns (plural, -ing, -ed) por regras simples ou tabela de aliases.
4. Aplicar **lista de exclusão** para palavras muito comuns, a menos que o contexto confirme o domínio (ex.: "model", "token", "layer" exigem palavras de apoio na janela de contexto ou etiqueta de domínio forte).
5. Aplicar **cooldown** por termo e **orçamento de pop-ups por minuto**.
6. Candidato desconhecido: substantivos/sintagmas raros (frequência baixa em lista geral do inglês) em contexto técnico podem ir ao caminho LLM, com limite de taxa próprio.

## 5. Transcrição em tempo real (especificação)

- Modelos de partida: Whisper **somente inglês** (`small.en` ou variante destilada), quantizado para CPU. Calibrar no benchmark.
- Segmentação por VAD, com limite máximo de segmento (ex.: 8–12 s) e pequena sobreposição (ex.: 0,3–0,5 s) para não cortar palavras.
- Dica de vocabulário: lista dos termos de maior prioridade do domínio, truncada ao tamanho permitido pelo modelo. Ver regra no `05-prompts.md`.
- Provedor Groq: respeitar os limites do plano gratuito (ver `06-referencias.md`), enviar segmentos de **no mínimo ~10 s** devido à cobrança mínima por requisição, aceitando latência maior; reduzir requisições com VAD.
- Duas fontes simultâneas: processar em filas separadas, com limite de concorrência para não saturar CPU.

## 6. Modelo de dados (SQLite)

Arquivo único por usuário, em pasta de dados do aplicativo.

### Tabelas principais

| Tabela | Campos principais |
|---|---|
| `domain` | `id`, `slug`, `name`, `version`, `license`, `active` |
| `term` | `id`, `domain_id`, `canonical_en`, `pos`, `priority`, `is_ambiguous`, `stoplisted` |
| `term_alias` | `term_id`, `alias`, `kind` (plural, sigla, variação) |
| `sense` | `id`, `term_id`, `ordinal`, `domain_tag`, `translation_pt`, `definition_pt`, `register` (ex.: arcaico), `example_en` |
| `term_i18n` | `sense_id`, `lang`, `translation`, `definition` (para outros idiomas de saída) |
| `term_fts` | índice FTS5 sobre termos e aliases |
| `sense_vec` | embedding por acepção (tabela virtual de vetores) |
| `session` | `id`, `started_at`, `ended_at`, `title`, `audio_sources` |
| `detection` | `id`, `session_id`, `term_id`, `sense_id`, `at`, `source`, `method`, `context_snippet?`, `learned` |
| `generated_entry` | `id`, `term`, `definition`, `model`, `created_at`, `approved` |
| `setting` | `key`, `value` |

Observações:
- `context_snippet` é **opcional** e desligado por padrão (privacidade).
- Entradas geradas ficam separadas de `term/sense` até o usuário aprová-las.
- Migrações versionadas desde o início.

## 7. Pacote de domínio (formato de distribuição)

Arquivo compactado contendo:
- `manifest` (slug, nome, versão, idioma-fonte, idiomas disponíveis, licença, autores, data);
- `terms` (JSON/CSV conforme `07-glossario-seed-modelo.md`);
- `vectors` (opcional, embeddings pré-calculados com o modelo e versão declarados);
- `stoplist` e `context_hints` do domínio.

Instalar um pacote = inserir nas tabelas acima e recalcular vetores se o modelo de embedding for diferente.

## 8. Especificação do pop-up

### Visual (referência: print de dicionário do projeto)
- Cartão compacto, fundo claro e cor de destaque quente; **termo** em negrito e cor de destaque; linha de **classe** (ex.: "substantivo") em cor secundária; **acepções numeradas**, com a relevante em destaque e as demais opcionais (expandir por clique); rótulos de registro como *arcaico* em itálico e cor distinta.
- Tamanho máximo configurável (ex.: 360×200 px), cantos arredondados, sombra leve.
- Posição configurável (canto inferior direito por padrão), com margem da borda.
- Modo claro/escuro.

### Comportamento
- Janela sem borda, **sempre no topo**, **sem receber foco** e **sem ativar** ao aparecer.
- Opção de "transparente a cliques" enquanto não há hover.
- Entrada/saída com animação curta (≤ 200 ms), desativável.
- Tempo de exibição padrão 6–8 s; pausa no hover; clique fecha; ação "fixar".
- Fila: no máximo N cartões simultâneos (padrão 3); novos substituem os mais antigos.
- Respeitar múltiplos monitores e DPI.
- Nunca capturar o próprio áudio do app (sem sons).

## 9. Configuração (campos)

- Fontes de áudio e dispositivos; ganho/limiar do VAD.
- Provedor de STT (local/Groq), modelo, chave Groq (armazenada localmente, de preferência no cofre de credenciais do SO).
- Provedor de LLM (local/Groq/desligado), modelo.
- Domínios ativos, idioma de saída, cooldown, orçamento por minuto, duração, posição, tema.
- Privacidade: salvar contexto (sim/não), salvar transcrição (padrão não), limpar histórico.
- Atalhos globais.

## 10. Privacidade e segurança

- Processamento local por padrão; áudio mantido em memória e descartado após uso.
- Provedor em nuvem **opt-in**, com aviso, indicador permanente e possibilidade de revogar a qualquer momento.
- Chaves de API nunca em texto puro nos logs; logs sem conteúdo de fala por padrão.
- Aviso de consentimento na primeira execução (LGPD/uso em reuniões).
- Dados do usuário não saem do computador, salvo o que o provedor escolhido receber.

## 11. Portabilidade

| Plataforma | Captura de áudio de saída | Observações |
|---|---|---|
| Windows | Loopback WASAPI | Alvo do protótipo |
| Linux | Fonte "monitor" do PipeWire/PulseAudio | Direto |
| macOS | Dispositivo virtual (ex.: BlackHole) ou API de captura de tela/áudio do sistema | Exige permissão do usuário (verificar versão do SO) |
| Android | Captura de áudio de reprodução com restrições por app (verificar) | Provável apenas microfone na prática |
| iOS | Muito restrito | Provável apenas microfone |

## 12. Observabilidade

- Log local com níveis; métricas de sessão: latência por etapa, taxa de pop-ups, falsos positivos marcados pelo usuário (botão "irrelevante").
- Modo "benchmark" que processa um arquivo de áudio e compara com anotações (ver `04-roadmap.md`).

## 13. Decisões em aberto

1. Modelo de embedding exato (tamanho vs. qualidade em inglês técnico + português).
2. LLM local mínimo viável e se vale incluí-lo no instalador ou baixar sob demanda.
3. Estratégia de lematização leve sem dependências pesadas.
4. Distribuição do glossário seed (licença e curadoria).
5. Framework de UI definitivo se o instalador ficar grande.
