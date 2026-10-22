# Mapa de fluxos do Sopro

Esta pasta reúne os **fluxos de usuário, de sistema e de engenharia** do Sopro em
documentos curtos, cada um com texto explicativo e um diagrama Mermaid. Ela complementa —
e não substitui — o [roadmap de produto](../04-roadmap.md): aqui o recorte é **como o
sistema se comporta hoje e como cada parte se conecta**, não a ordem cronológica das fases.

Os diagramas são renderizados no GitHub, em IDEs com suporte a Mermaid e em ferramentas
como o Mermaid Live Editor. Cada documento também explica o fluxo em texto, para leitura
sem renderização.

## Como ler os fluxos

| Marca | Significado |
|---|---|
| `implementado` | O fluxo existe no código e é coberto por testes ou uso manual. |
| `parcial` | O núcleo existe, mas alguma superfície de UI ou automação ainda está em evolução. |
| `planejado` | Direção documentada; não trate como comportamento disponível. |

## Mapa sugerido

| Documento | Fluxo | Público principal | Estado |
|---|---|---|---|
| [01-visao-geral.md](01-visao-geral.md) | Visão geral do sistema, camadas, limites e dependências | Todos | implementado |
| [02-jornada-do-usuario.md](02-jornada-do-usuario.md) | Primeira execução e uso no dia a dia | Produto, UX, suporte | implementado |
| [03-captura-de-audio.md](03-captura-de-audio.md) | Captura do sistema e do microfone, VAD e indicador | Engenharia de áudio | implementado |
| [04-transcricao.md](04-transcricao.md) | Seleção do STT, download do modelo, dica de vocabulário e fallback | Engenharia de IA | implementado |
| [05-deteccao-e-decisao.md](05-deteccao-e-decisao.md) | Normalização, matcher, stoplist, cooldown e orçamento | Núcleo, QA | implementado |
| [06-resolucao-de-acepcoes.md](06-resolucao-de-acepcoes.md) | Cascata de desambiguação, RAG, trilhas e LLM | Núcleo, IA, QA | implementado |
| [07-popups-e-historico.md](07-popups-e-historico.md) | Fila de cartões, overlay, persistência e histórico | UI, produto | implementado |
| [08-glossarios-e-trilhas.md](08-glossarios-e-trilhas.md) | Pacotes de domínio, trilhas, importação e agregação | Núcleo, conteúdo | implementado |
| [09-construcao-de-glossario.md](09-construcao-de-glossario.md) | Passo a passo para criar um glossário ou uma trilha | Contribuidores | implementado |
| [10-modelos-e-llm.md](10-modelos-e-llm.md) | Modelos locais, provedores em nuvem, consentimento e cache | IA, privacidade | implementado |
| [11-configuracoes-e-bandeja.md](11-configuracoes-e-bandeja.md) | Hub, configurações, bandeja, indicador, atalhos e instância única | UI, produto | parcial |
| [12-dados-e-persistencia.md](12-dados-e-persistencia.md) | SQLite, migrações, sessões, histórico, logs e pastas | Engenharia de dados | implementado |
| [13-build-e-release.md](13-build-e-release.md) | Do código ao executável, instalador, hashes e CI | Maintainers | implementado |
| [14-testes-e-qualidade.md](14-testes-e-qualidade.md) | Pirâmide de testes, validação de glossário e portões de qualidade | QA, contribuidores | implementado |

## Trilhas de leitura

- **Quero usar o Sopro:** comece em [02-jornada-do-usuario.md](02-jornada-do-usuario.md)
  e consulte [11-configuracoes-e-bandeja.md](11-configuracoes-e-bandeja.md).
- **Quero entender a arquitetura:** leia [01-visao-geral.md](01-visao-geral.md), depois
  [03-captura-de-audio.md](03-captura-de-audio.md) a
  [07-popups-e-historico.md](07-popups-e-historico.md) na ordem.
- **Quero contribuir com conteúdo:** leia
  [09-construcao-de-glossario.md](09-construcao-de-glossario.md) e o
  [CONTRIBUTING.md](../../CONTRIBUTING.md).
- **Quero contribuir com código:** leia [01-visao-geral.md](01-visao-geral.md),
  [12-dados-e-persistencia.md](12-dados-e-persistencia.md),
  [14-testes-e-qualidade.md](14-testes-e-qualidade.md) e o
  [CONTRIBUTING.md](../../CONTRIBUTING.md).
- **Quero publicar uma versão:** leia [13-build-e-release.md](13-build-e-release.md).

## Fluxos que valem manter no radar

Os documentos acima cobrem o caminho principal. Se o projeto crescer, estes fluxos merecem
documentos próprios ou seções novas:

1. **Onboarding guiado por diagnóstico**: detectar ausência de dispositivo, permissão ou
   modelo e conduzir a correção sem abrir chamado.
2. **Revisão colaborativa de glossário**: propor termo, revisar acepção, aprovar e publicar
   com histórico de autoria.
3. **Curadoria por IA com proveniência**: livros e artigos viram candidatos, clusters e
   rótulos, sempre com fonte registrada e revisão humana.
4. **Sincronização opcional de preferências**: hoje tudo é local; qualquer sincronização
   futura precisa de consentimento explícito e criptografia.
5. **Portabilidade Linux/macOS**: mesma arquitetura, outra implementação de `AudioSource`.
6. **Feedback do usuário**: botão "irrelevante" alimentando stoplist e ranking por domínio.

## Convenções para atualizar um fluxo

- O diagrama deve caber em uma tela; detalhes vão no texto.
- Use os nomes reais dos módulos e contratos (`DetectionService`, `SenseResolver`,
  `aggregate_packages`, `PopupQueue`).
- Marque explicitamente o que é local, o que é opcional e o que sai do computador.
- Ao mudar um fluxo, atualize o diagrama, a tabela do índice e o
  [README](../../README.md#arquitetura) na mesma alteração.
