# Pacote de domínio: `tech-en-pt`

Glossário seed de **Tecnologia e IA** (inglês → português do Brasil), no formato
definido em [`docs/07-glossario-seed-modelo.md`](../../../docs/07-glossario-seed-modelo.md).

## Conteúdo

| Arquivo | Descrição |
|---|---|
| `manifest.json` | Manifesto do pacote (slug, nome, versão, idiomas, licença, autores). |
| `terms.json` | Termos e acepções (uma entrada por termo). |
| `stoplist.txt` | Palavras comuns que só disparam pop-up com contexto de domínio. |

## Versão

`0.1.0` — primeiro lote seed. Ainda **não curado**: todos os termos estão com
`needs_review=true`. Definir licença e autores antes de distribuir (ver
`docs/06-referencias.md`).

## Validação

```bash
sopro-validate-glossary data/domains/tech-en-pt
sopro-validate-glossary data/domains/tech-en-pt --json
```

O validador aplica o **checklist de `docs/07` §6** e as regras de qualidade de §5:
duplicatas de `canonical_en`, termos ambíguos sem acepção do domínio, aliases
colidindo com a stoplist, faixa de `priority` (1–5), limites de definição (≤ 25
palavras), presença de manifesto e pendências de revisão.

## Convenções

- A **etiqueta de domínio** é derivada do prefixo do `slug` (`tech-en-pt` → `tech`).
  Toda acepção voltada a tecnologia usa `domain_tag: "tech"`; sentidos de dicionário
  comum usam `domain_tag: "general"`.
- Termos ambíguos e/ou `stoplisted` trazem `context_hints` para a desambiguação.
- Definições: ≤ 25 palavras, neutras, em português do Brasil.
