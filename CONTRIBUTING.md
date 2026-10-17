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
   sopro-validate-glossary data/domains/tech-en-pt
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

## Glossários e conteúdo

- Siga o formato de [docs/07-glossario-seed-modelo.md](docs/07-glossario-seed-modelo.md).
- Definições: ≤ 25 palavras, neutras, em português do Brasil.
- Registre **licença e origem** de cada pacote. Conteúdo de terceiros exige verificação de licença (ver [docs/06-referencias.md](docs/06-referencias.md)).
- Entradas marcadas como `gerado` nunca viram curadas sem revisão humana (`needs_review=false` só após revisão).

## Testes

- Todo código de núcleo precisa de testes.
- Fixtures de exemplo do glossário: use as entradas de [docs/07-glossario-seed-modelo.md](docs/07-glossario-seed-modelo.md).

## Reportando bugs e sugerindo melhorias

Abra uma issue incluindo: o que esperava, o que aconteceu, passos para reproduzir, e (se aplicável) SO, versão do Python e logs **sem conteúdo de fala**.

## Licença das contribuições

Ao contribuir, você concorda em licenciar sua contribuição sob a licença do projeto (a definir — ver [LICENSE](LICENSE)).
