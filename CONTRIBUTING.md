# Contribuindo com o Sopro

Obrigado pelo interesse! Este documento resume como propor mudanças de forma produtiva.

Ao participar, você concorda com o [Código de Conduta](CODE_OF_CONDUCT.md).

## Antes de começar

1. Leia a [Visão e requisitos](docs/01-visao-e-requisitos.md) e a [Arquitetura](docs/02-arquitetura-e-especificacoes.md).
2. Verifique o [Roadmap](docs/04-roadmap.md) para saber em que fase estamos.
3. Siga as regras de trabalho do **Prompt-mestre** em [docs/05-prompts.md](docs/05-prompts.md):
   - planeje antes de codificar;
   - entregue passos pequenos e testáveis;
   - testes para a lógica do núcleo (matcher, resolvedor de acepção, repositório);
   - não adicione dependências pesadas sem justificar tamanho e licença.

## Ambiente de desenvolvimento

Requisitos: Python 3.11+.

```bash
python -m venv .venv
. .venv/Scripts/activate        # Windows (Git Bash)
# source .venv/bin/activate     # Linux/macOS
python scripts/tasks.py install # instala .[dev,ui,audio,stt]
```

Use o task runner `scripts/tasks.py` para as tarefas do dia a dia (`test`, `dev`, `demo`,
`bench`, `validate`, `build`). Detalhes do fluxo local, modo demo e empacotamento portátil
em [docs/10-dev-workflow.md](docs/10-dev-workflow.md).

## Fluxo de trabalho

1. Crie uma branch descritiva: `feat/matcher-n-gramas`, `fix/validador-stoplist`, `docs/roadmap`.
2. Faça commits pequenos e atômicos. Use [Conventional Commits](https://www.conventionalcommits.org/):
   `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`.
3. Garanta que tudo passa antes de abrir PR:
   ```bash
   pytest -q
   sopro-validate-glossary data/domains --all --strict
   ```
4. Abra um Pull Request explicando **o que**, **por quê** e **como testar**.

## Regras de arquitetura (obrigatórias)

- `src/sopro/core/**` **nunca** importa de `platform`, de GUI ou de APIs de SO.
- `src/sopro/platform/**` isola tudo que depende de SO/UI (áudio, pop-up).
- Novas capacidades de plataforma entram atrás de interfaces (ex.: `AudioSource`, `STTProvider`, `LLMProvider`).

## Padrões de código

- Não adicione comentários explicando o óbvio; nomes claros valem mais.
- Sem dependências pesadas sem justificativa de tamanho e licença (RNF-12).
- Erros de rede/provedor: degradação graciosa, nunca derrubar o app (RNF-10).
- Sem telemetria; áudio não é gravado em disco por padrão (RNF-09).
- Não invente assinaturas de API: confirme na documentação oficial.

## Criando um glossário ou uma trilha

Conteúdo é bem-vindo e **não deve exigir mudanças no núcleo**. Um glossário é um **pacote de
domínio**; uma trilha é um pacote filho do mesmo domínio. Se o formato atual não acomodar a
sua contribuição, abra uma issue antes de alterar `core`.

O fluxo visual completo está em
[docs/roadmap/09-construcao-de-glossario.md](docs/roadmap/09-construcao-de-glossario.md).

### Estrutura do pacote

```text
data/domains/<slug>/
  manifest.json    # identidade, versão, licença, autores e trilha
  terms.json       # termos, aliases, acepções e hints de contexto
  stoplist.txt     # palavras comuns que exigem contexto
```

Para uma trilha, o manifesto inclui os campos que a ligam ao domínio pai:

```json
{
  "slug": "tech-devops-en-pt",
  "parent_slug": "tech-en-pt",
  "track": "devops",
  "track_label": "DevOps, SRE e Infraestrutura",
  "track_order": 2
}
```

Um pacote base **não** declara `parent_slug` nem `track`. O `track_order` define a ordem de
exibição e de preferência das acepções.

### Passo a passo

1. **Escolha o tipo e o slug.** Use o padrão `<área>-en-pt` para a base e
   `<área>-<trilha>-en-pt` para a trilha. Evite slugs genéricos ou duplicados.
2. **Crie a pasta e o manifesto.** Preencha `name`, `version` (comece em `0.1.0`), `license`,
   `authors` e `created_at`. Em trilha, preencha também `parent_slug`, `track`,
   `track_label` e `track_order`.
3. **Escreva `terms.json`.** Use `canonical_en`, `aliases`, `priority`, `senses`,
   `context_hints`, `source` e `needs_review`. Em trilha, use `tracks` no termo e `track` na
   acepção específica. A definição deve ter até 25 palavras, ser neutra e estar em português
   do Brasil.
4. **Ajuste a stoplist.** Palavras comuns (`model`, `token`, `layer`, `class`…) entram na
   stoplist e só disparam com um `context_hint` na janela de contexto.
5. **Documente a origem.** Registre a licença no manifesto e crie
   `docs/trilhas/<trilha>.md` com descrição, público, fontes e notas de curadoria. Conteúdo de
   terceiros exige verificação de licença; consulte
   [docs/06-referencias.md](docs/06-referencias.md) e
   [docs/07-glossario-seed-modelo.md](docs/07-glossario-seed-modelo.md).
6. **Valide o pacote e a composição.**

   ```bash
   sopro-validate-glossary data/domains --all --strict
   pytest -q
   ```

7. **Teste em um banco isolado**, sem tocar nos seus dados reais:

   ```bash
   SOPRO_HOME=/tmp/sopro-glossario python -m sopro --demo --domains-root data/domains
   ```

   No PowerShell: `$env:SOPRO_HOME = "$env:TEMP\sopro-glossario"`.

8. **Revise uma amostra de pelo menos 20 termos.** Só marque `needs_review=false` após
   revisão humana. Entradas com `source: "generated"` ou `source: "llm"` nunca entram como
   curadas sem essa etapa.
9. **Abra o PR** com o pacote, a página em `docs/trilhas/` e a saída dos comandos de validação.

### Regras de trilha e agregação

- A base tem precedência sobre a trilha em metadados do mesmo termo; as acepções são somadas.
- Um termo pode pertencer a várias trilhas; o runtime deduplica por `canonical_en`.
- A trilha ativa ganha prioridade na resolução de acepções; `active_tracks` vazio significa
  “todas as trilhas”.
- A detecção é persistida no domínio de origem, não no pacote agregado.
- Trilha sem `parent_slug`, com pai inexistente ou ciclo é rejeitada pelo validador.

### Checklist de qualidade

- [ ] Manifesto e `terms.json` passam em `--strict`.
- [ ] Definições curtas, neutras e sem opinião.
- [ ] Pelo menos 20 termos revisados por humano.
- [ ] Stoplist e `context_hints` testados contra falsos positivos.
- [ ] Licença e fontes registradas.
- [ ] Página em `docs/trilhas/` criada.
- [ ] Importação e agregação testadas em banco isolado.

### Curadoria assistida por IA — fase futura

O projeto prevê uma **Fase 6** para transformar livros e artigos em candidatos com
proveniência, sem publicar automaticamente. O pipeline planejado é:

1. **Fontes e proveniência**: registrar obra, edição, página/capítulo, licença e hash.
2. **Extração de candidatos**: BoW/TF-IDF e n-gramas para levantar termos recorrentes.
3. **Embeddings e clusters**: BERTopic/HDBSCAN para agrupar termos por tema.
4. **Rótulos e definições**: LLM propõe nome da trilha, tradução e definição curta.
5. **Revisão humana**: aprovar, editar ou rejeitar; nada entra como curado sem revisão.
6. **Publicação**: gerar o pacote e a página de fontes com rastreabilidade completa.

Até essa fase existir, contribuições manuais seguem o fluxo acima. Não use LLM para marcar
termos como revisados.

### Quando o código precisa mudar

Só quando o **formato** muda. Nesse caso, a alteração deve tocar, no mínimo:
`package.py`, `models.py`, `migrations.py`, `repository.py`, `importer.py`, `validate.py` e
testes de ida e volta (importar, exportar, reimportar). Mudanças de formato são incompatíveis
e exigem discussão prévia.

## Testes

- Todo código de núcleo precisa de testes.
- Fixtures de exemplo do glossário: use as entradas de [docs/07-glossario-seed-modelo.md](docs/07-glossario-seed-modelo.md).
- Conteúdo novo também precisa passar em `sopro-validate-glossary data/domains --all --strict`.

## Reportando bugs e sugerindo melhorias

Abra uma issue incluindo: o que esperava, o que aconteceu, passos para reproduzir, e (se aplicável) SO, versão do Python e logs **sem conteúdo de fala**.

## Licença das contribuições

Ao contribuir, você concorda em licenciar sua contribuição sob a licença do projeto (a definir — ver [LICENSE](LICENSE)).
