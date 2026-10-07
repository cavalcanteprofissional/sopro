# Sopro

**Um companheiro discreto que explica termos técnicos em inglês no momento exato em que eles são falados.**

Você está vendo uma aula, palestra ou call técnica em inglês e ouve *"fairness"* ou *"backlog"* passar rápido. Pesquisar quebra a atenção. Legenda automática não explica o termo nem escolhe o sentido certo para a área.

O Sopro resolve assim: escuta o áudio do seu PC (ou do microfone), detecta o termo quando é falado e mostra um cartão curto com o termo, a tradução e a definição no contexto da área — sem interromper a aula e sem roubar o foco da janela.

## Destaques

- **Pop-up por termo, não legenda corrida** — cartão temporário, sempre no topo, sem roubar foco do Teams/Meet/Zoom.
- **Local primeiro** — roda 100% offline por padrão; nuvem (Groq) é opcional e só com aviso explícito.
- **Definição certa para a área** — recuperação semântica escolhe a acepção correta (ex.: *fairness* = "equidade" em IA, não "justiça" genérica).
- **Privacidade** — áudio não é gravado em disco; sem telemetria; dados não saem do computador.
- **Só free tier** — Whisper local, SQLite, ferramentas gratuitas.
- **Escalável** — glossários por domínio: tecnologia hoje, direito/saúde/finanças depois.

## Status

Projeto em fase de **planejamento e especificação**. Esta repositório contém a documentação completa que orienta a implementação.

## Documentação

| Arquivo | O que tem |
|---|---|
| [01-visao-e-requisitos.md](01-visao-e-requisitos.md) | O problema, a visão, requisitos (RF/RNF/RN) e critérios de aceite |
| [02-arquitetura-e-especificacoes.md](02-arquitetura-e-especificacoes.md) | Pipeline, módulos, contratos, modelo de dados e especificação do pop-up |
| [03-estado-da-arte.md](03-estado-da-arte.md) | Pesquisa de soluções existentes e a lacuna que o Sopro preenche |
| [04-roadmap.md](04-roadmap.md) | Fases de implementação, métricas, riscos e marcos |
| [05-prompts.md](05-prompts.md) | Prompts para desenvolvimento (por fase) e para o runtime do app |
| [06-referencias.md](06-referencias.md) | Links, bibliotecas, limites de free tier e notas legais |

## Como funciona (resumo)

```
Áudio (saída do PC / microfone)
   → detecção de fala (VAD)
   → transcrição em tempo real (Whisper local)
   → busca no glossário do domínio ativo
   → escolha da acepção pelo contexto (RAG)
   → pop-up com termo, tradução e definição
   → registro no histórico local (SQLite)
```

O LLM **não** processa toda frase: o caminho rápido é busca em glossário local. RAG/LLM só entra para resolver ambiguidade ou termos fora do glossário — isso mantém latência, CPU e custo baixos.

## Roadmap em 5 fases

1. **Validação** — glossário seed e conjunto de teste anotado
2. **Pipeline em CLI** — captura, VAD, transcrição e matcher medidos
3. **Overlay e persistência** — pop-up, SQLite, configurações
4. **RAG e desambiguação** — acepção contextual + provedor Groq opcional
5. **Empacotamento** — instalador Windows e primeira execução

Detalhes e definições de pronto em [04-roadmap.md](04-roadmap.md).

## Privacidade e legal

- Processamento local por padrão; áudio fica em memória e é descartado.
- Provedor em nuvem só com opt-in, aviso e indicador permanente.
- Gravar/transcrever reuniões pode exigir consentimento dos participantes (LGPD — Lei 13.709/2018). O app exibe aviso na primeira execução.

## Licença

A definir — pendente de revisão das licenças dos glossários e fontes (ver [06-referencias.md](06-referencias.md)).
