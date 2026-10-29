# 08 — Glossários, trilhas e agregação

**Estado:** implementado no núcleo; a seleção visual dedicada de trilhas é parcial.

Um **domínio** é um pacote de conhecimento (por exemplo, tecnologia). Uma **trilha** é um
sub-pacote do mesmo domínio (programação, dados, DevOps, frontend, backend). A trilha não
muda o `domain_tag`; ela refina o vocabulário e as acepções.

## Estrutura de arquivos

```text
data/domains/
  tech-en-pt/                  base: conceitos transversais
    manifest.json
    terms.json
    stoplist.txt
  tech-programming-en-pt/      trilha: parent_slug = tech-en-pt
    manifest.json
    terms.json
    stoplist.txt
  tech-data-science-en-pt/
  tech-devops-en-pt/
  tech-frontend-en-pt/
  tech-backend-en-pt/
```

## Do arquivo ao runtime

```mermaid
flowchart TD
    BASE["Pacote base\ntech-en-pt"] --> VAL["Validador\ndocs/07 §6"]
    TRACK["Pacotes de trilha\ntech-*-en-pt"] --> VAL
    VAL --> OK{"Sem erros?"}
    OK -->|não| FIX["Corrige manifesto,\ntermos ou stoplist"]
    FIX --> VAL
    OK -->|sim| IMPORT["import_package()\nupsert no SQLite"]

    IMPORT --> DB[("domain\nterm\nsense\nterm_alias\nstoplist")]
    DB --> ACTIVE{"Trilhas ativas\nem Settings"}
    ACTIVE -->|lista vazia| ALL["Todas as trilhas\ndo domínio"]
    ACTIVE -->|lista preenchida| SOME["Somente as\nselecionadas"]
    ALL --> AGG["aggregate_packages()"]
    SOME --> AGG
    BASE --> AGG

    AGG --> MERGE["Dedup por canonical_en\nbase tem precedência"]
    MERGE --> SENSES["Senses mescladas\nordinais únicos\nordem: trilha, genérica, demais"]
    SENSES --> STOP["Stoplist unificada"]
    STOP --> PACKAGE["Pacote agregado\nem memória"]
    PACKAGE --> MATCH["Matcher"]
    PACKAGE --> RAG["SenseResolver\nembed_aggregate()"]

    MATCH --> DET["DetectionService"]
    RAG --> DET
    DET --> SAVE["Persiste no domínio\nde origem do termo"]
```

## Regras de composição

| Situação | Resultado |
|---|---|
| Termo só na base | Permanece genérico |
| Termo só na trilha | Entra no agregado com `tracks` da trilha |
| Termo na base e na trilha | Metadados da base vencem; acepções são somadas |
| Mesmo termo em duas trilhas ativas | Uma entrada; acepções das duas trilhas são preservadas |
| Trilha inativa | Seus termos e acepções ficam fora do agregado |
| `tracks_mode="all"` | Todas as trilhas filhas da base são carregadas |
| `tracks_mode="base"` | Somente a base, sem trilhas |
| `tracks_mode="custom"` | Apenas as trilhas listadas em `active_tracks` |
| `active_domains` aponta para trilha | A base é inferida por `parent_slug` |

## Por que agregar em vez de importar tudo

- O matcher precisa de uma visão única, sem termos duplicados.
- O resolvedor precisa de ordinais estáveis por termo.
- A UI e o histórico persistem a detecção no **domínio de origem**, não no agregado.
- A seleção de trilhas muda o vocabulário e o RAG sem exigir reinstalação.

## Detalhes de implementação

- `parent_slug` vazio identifica o pacote base; `track` vazio também.
- `track_order` define a ordem de exibição e de preferência.
- `term.tracks` lista as trilhas do termo; `sense.track` marca a acepção específica.
- `build_aggregate_from_repo(repo, base_slug, active_tracks)` carrega tudo do SQLite.
- A UI usa a árvore compartilhada `platform/popup/glossary_tree.py` em Glossários,
  Configurações e primeira execução; a seleção é persistida em `tracks_mode` +
  `active_tracks`.

## Criação de um novo glossário

O passo a passo para contribuidores está em
[09-construcao-de-glossario.md](09-construcao-de-glossario.md) e no
[CONTRIBUTING.md](../../CONTRIBUTING.md#criando-um-glossário-ou-uma-trilha).

## Ligações

- Formato detalhado: [docs/07 §7](../07-glossario-seed-modelo.md)
- Resolução: [06-resolucao-de-acepcoes.md](06-resolucao-de-acepcoes.md)
- Dados: [12-dados-e-persistencia.md](12-dados-e-persistencia.md)
