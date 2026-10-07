# 07 — Glossário seed: formato e exemplos

Define o formato dos **pacotes de domínio** e traz entradas de exemplo. As definições abaixo são rascunhos para validar o formato; **revise antes de usar** como glossário curado.

## 1. Formato JSON (entrada de termo)

```json
{
  "canonical_en": "string",
  "pos": "noun | verb | adjective | acronym | phrase",
  "aliases": ["plural, sigla, variações comuns"],
  "priority": 1,
  "is_ambiguous": false,
  "stoplisted": false,
  "context_hints": ["palavras que reforçam o domínio quando o termo é comum"],
  "senses": [
    {
      "ordinal": 1,
      "domain_tag": "tech | general | ...",
      "translation_pt": "string",
      "definition_pt": "até 25 palavras",
      "register": "arcaico | informal | null",
      "example_en": "frase curta"
    }
  ],
  "source": "curado | gerado",
  "needs_review": false
}
```

### Campos

| Campo | Regra |
|---|---|
| `priority` | 1 (alta) a 5 (baixa); alimenta a dica de vocabulário do Whisper |
| `is_ambiguous` | `true` se há mais de uma acepção relevante |
| `stoplisted` | `true` para palavras comuns que só disparam com contexto de domínio |
| `context_hints` | usados quando `stoplisted=true` ou `is_ambiguous=true` |
| `domain_tag` | marca a acepção do domínio; `general` para sentidos de dicionário comum |
| `register` | rótulos como *arcaico* aparecem em itálico no pop-up |
| `source` | `gerado` exige revisão antes de virar curado |

### Manifesto do pacote

```json
{
  "slug": "tech-en-pt",
  "name": "Tecnologia e IA (EN→PT)",
  "version": "0.1.0",
  "source_lang": "en",
  "output_langs": ["pt-BR"],
  "license": "definir",
  "authors": ["definir"],
  "created_at": "2026-10-07",
  "embedding_model": null
}
```

## 2. Formato CSV equivalente (para edição em planilha)

Colunas: `canonical_en, pos, aliases(;), priority, is_ambiguous, stoplisted, context_hints(;), sense_ordinal, domain_tag, translation_pt, definition_pt, register, example_en, source, needs_review`

Uma linha por acepção; termos com várias acepções repetem `canonical_en`.

## 3. Entradas de exemplo

### 3.1 fairness (caso do print do projeto)

```json
{
  "canonical_en": "fairness",
  "pos": "noun",
  "aliases": ["fair", "fairness metric"],
  "priority": 1,
  "is_ambiguous": true,
  "stoplisted": false,
  "context_hints": ["model", "bias", "dataset", "discrimination", "protected attribute"],
  "senses": [
    {"ordinal": 1, "domain_tag": "tech", "translation_pt": "equidade (algorítmica)",
     "definition_pt": "Princípio de que um modelo não deve gerar resultados sistematicamente desfavoráveis a grupos específicos.",
     "register": null, "example_en": "We evaluated the model's fairness across demographic groups."},
    {"ordinal": 2, "domain_tag": "general", "translation_pt": "imparcialidade, justiça, equidade",
     "definition_pt": "Qualidade de tratar pessoas ou situações de modo justo e sem favoritismo.",
     "register": null, "example_en": "The judge was known for her fairness."},
    {"ordinal": 3, "domain_tag": "general", "translation_pt": "brancura",
     "definition_pt": "Característica de pele ou aspecto claro.", "register": null, "example_en": null},
    {"ordinal": 4, "domain_tag": "general", "translation_pt": "qualidade do que é louro",
     "definition_pt": "Característica de cabelos claros.", "register": null, "example_en": null},
    {"ordinal": 5, "domain_tag": "general", "translation_pt": "beleza",
     "definition_pt": "Sentido antigo de beleza.", "register": "arcaico", "example_en": null}
  ],
  "source": "curado",
  "needs_review": true
}
```

> No pop-up, apenas a acepção 1 aparece em destaque (domínio tecnologia); as demais ficam recolhidas.

### 3.2 Termos adicionais (versão compacta)

| canonical_en | aliases | acepções (domínio tech em **negrito**) | definição curta (rascunho) |
|---|---|---|---|
| overfitting | overfit, overfitted | **sobreajuste** | Quando o modelo decora os dados de treino e generaliza mal para dados novos. |
| embedding | embeddings | **vetor de representação (embedding)** | Vetor numérico que representa texto, imagem ou outro dado capturando relações de significado. |
| gradient descent | SGD (relacionado) | **descida do gradiente** | Algoritmo que ajusta parâmetros passo a passo na direção que reduz o erro do modelo. |
| token | tokens, tokenization | **token** (unidade de texto); credencial de acesso; ficha | Em NLP, pedaço de texto (palavra ou fragmento) que o modelo processa como unidade. |
| bias | biases | **viés** (dados/modelo); termo de viés (parâmetro); tendência (geral) | Distorção sistemática nos dados ou no modelo que leva a resultados enviesados. |
| hallucination | hallucinate, hallucinations | **alucinação** | Quando um modelo gera informação plausível, porém falsa ou sem base. |
| fine-tuning | fine-tune, finetuning | **ajuste fino** | Treinar novamente um modelo já treinado com dados específicos para uma tarefa. |
| inference | infer | **inferência** | Uso de um modelo treinado para produzir previsões ou respostas com novos dados. |
| RAG | retrieval-augmented generation | **geração aumentada por recuperação** | Técnica que busca documentos relevantes e os fornece ao modelo antes de gerar a resposta. |
| backlog | product backlog | **backlog** (lista de pendências do produto) | Lista priorizada de tarefas e requisitos a serem desenvolvidos pela equipe. |
| latency | — | **latência** | Tempo entre uma solicitação e o início ou fim da resposta. |
| transformer | transformers | **transformer** (arquitetura); transformador (elétrico) | Arquitetura de rede neural baseada em atenção, base dos modelos de linguagem atuais. |

> `token`, `bias`, `transformer`, `model`, `layer`, `kernel` e `pipeline` são ambíguos ou comuns: marcar `is_ambiguous=true` e, quando necessário, `stoplisted=true` com `context_hints`.

## 4. Stoplist inicial (candidatas)

Palavras que só devem disparar com contexto de domínio: `model, layer, kernel, pipeline, token, class, object, function, array, stack, queue, cloud, bug, patch, memory, driver`. Calibrar com o conjunto de teste e com o botão "irrelevante".

## 5. Regras de qualidade

1. Definição ≤ 25 palavras, neutra, em português do Brasil.
2. Uma acepção por significado; marcar a do domínio com `domain_tag`.
3. Siglas: forma expandida no `alias` ou na definição.
4. Sem invenção: se houver dúvida, `needs_review=true`.
5. Registrar a **licença** e a **origem** de cada pacote.
6. Entradas `gerado` nunca entram no pacote curado sem revisão humana.

## 6. Checklist de validação do pacote

- [ ] JSON/CSV válido e sem duplicatas de `canonical_en`
- [ ] Todo termo ambíguo tem ao menos uma acepção com `domain_tag` do domínio
- [ ] Aliases não colidem com palavras muito comuns
- [ ] Prioridades cobrem os termos mais frequentes das aulas de teste
- [ ] Manifesto com versão, idioma, licença e autores
- [ ] Amostra de 20 termos revisada manualmente
