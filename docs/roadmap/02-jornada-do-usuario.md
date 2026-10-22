# 02 — Jornada do usuário

**Estado:** implementado.

Este fluxo descreve o que a pessoa vê e decide, não os detalhes internos. Há dois momentos:
a **primeira execução** (consentimento, escolha de glossário/fontes e preparação do modelo) e
o **uso no dia a dia** (escutar, receber o cartão, consultar o histórico e ajustar
preferências).

## Primeira execução e uso diário

```mermaid
flowchart TD
    START["Abrir o Sopro"] --> LOCK{"Outra instância\njá está aberta?"}
    LOCK -->|sim| FOCUS["Traz o hub existente\npara frente"]
    LOCK -->|não| HOME["Resolve SOPRO_HOME\nabre SQLite e migra"]
    HOME --> FIRST{"Primeira execução?"}

    FIRST -->|sim| NOTICE["Aviso de consentimento\nLGPD e privacidade"]
    NOTICE --> ACCEPT{"Aceita?"}
    ACCEPT -->|não| EXIT["Encerra sem coletar áudio"]
    ACCEPT -->|sim| CHOOSE["Escolhe domínio/trilhas,\nidioma e fontes de áudio"]
    CHOOSE --> IMPORT["Importa pacotes locais\ne recalcula vetores"]
    IMPORT --> MODEL{"STT local\njá está em cache?"}
    MODEL -->|não| DOWNLOAD["Baixa modelo com progresso\nverifica SHA-256"]
    MODEL -->|sim| WARMUP["Warmup do modelo"]
    DOWNLOAD --> WARMUP
    WARMUP --> LISTEN["Escutando"]

    FIRST -->|não| SETTINGS["Carrega preferências salvas"]
    SETTINGS --> LISTEN

    LISTEN --> SPEECH["Fala detectada"]
    SPEECH --> CARD["Cartão: termo, tradução\ne definição"]
    CARD --> ACTION{"Ação do usuário"}
    ACTION -->|hover| PAUSE["Pausa o tempo do cartão"]
    ACTION -->|fixar| PIN["Mantém o cartão visível"]
    ACTION -->|fechar| DISMISS["Remove o cartão"]
    ACTION -->|nada| EXPIRE["Cartão expira sozinho"]

    PAUSE --> HISTORY
    PIN --> HISTORY
    DISMISS --> HISTORY
    EXPIRE --> HISTORY
    HISTORY["Histórico da sessão"] --> REVIEW["Busca, filtra,\nexporta CSV/Markdown"]

    LISTEN --> CONTROL{"Controle"}
    CONTROL -->|atalho/tray| TOGGLE["Pausar ou retomar"]
    CONTROL -->|tray/hub| CONFIG["Configurações"]
    CONTROL -->|tray/hub| GLOSSARY["Glossários e termos"]
    CONTROL -->|demo| DEMO["Demonstração sem áudio"]
    CONTROL -->|sair| QUIT["Encerra captura\ne fecha o app"]
    TOGGLE --> LISTEN
```

## O que o usuário percebe

| Momento | Feedback esperado |
|---|---|
| App abrindo | Indicador em `Carregando`; bandeja mostra o estado |
| Download do modelo | Progresso no indicador/bandeja, sem diálogo modal |
| Falha de áudio ou modelo | Estado `Erro`, mensagem curta e ação de tentar de novo |
| Escutando | Indicador pulsando com o nível de áudio |
| Analisando um trecho | Indicador em `Analisando` enquanto transcreve/resolve |
| Cartão exibido | Sem roubar foco; som opcional; hover pausa; fixar/ fechar |
| Pausado | Indicador em `Pausado`; nenhum novo cartão |
| Nuvem ativa | Sinal permanente na bandeja/hub |

## Decisões de produto embutidas

- **Consentimento antes de ouvir**: a primeira execução apresenta o aviso de privacidade e
  só segue com aceite.
- **Escolha explícita de fontes**: microfone e áudio do sistema podem ser ligados ou
  desligados independentemente.
- **Demonstração sem risco**: `--demo` exercita o pipeline com dados sintéticos, sem áudio
  real e sem download de modelo.
- **Fechar janelas não encerra o app**: o Sopro vive na bandeja; apenas “Sair” encerra.
- **Histórico é local**: exportar é uma ação do usuário; não há sincronização automática.

## Falhas e recuperação

| Situação | Comportamento |
|---|---|
| Nenhum dispositivo de áudio | Estado de erro com mensagem; o app permanece aberto |
| Modelo indisponível/offline | Falha clara; o usuário pode tentar de novo ou usar STT em nuvem, se configurado |
| Groq sem chave ou sem rede | Degradação para o provedor local |
| Glossário inválido | Importação recusada com erro; o pacote anterior continua ativo |
| Banco corrompido | O app não deve sobrescrever dados sem aviso; ver [12-dados-e-persistencia.md](12-dados-e-persistencia.md) |

## Ligações

- Configurações e bandeja: [11-configuracoes-e-bandeja.md](11-configuracoes-e-bandeja.md)
- Cartões e histórico: [07-popups-e-historico.md](07-popups-e-historico.md)
- Glossários: [08-glossarios-e-trilhas.md](08-glossarios-e-trilhas.md)
