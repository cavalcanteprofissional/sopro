# 03 — Estado da arte

> Pesquisa realizada em 07/10/2026 com busca na web. Descrições em paráfrase; confirme nas páginas oficiais antes de decisões de produto. Itens não verificados estão marcados.

## 1. Resposta curta

Nas buscas realizadas **não foi encontrado** um aplicativo que reúna: desktop standalone + áudio de saída e microfone + transcrição em tempo real + filtro por domínio + pop-up de glossário por termo + execução local. Existem soluções que cobrem **partes** da proposta.

## 2. Soluções encontradas (verificadas na pesquisa)

### 2.1 JargonLens (extensão de navegador)
- **O que faz:** lê as legendas do vídeo do YouTube e exibe definições em linguagem simples no instante em que um termo especializado é falado; inclui glossário por vídeo, navegação por tempo, filtro de termos já conhecidos e cache local de análises recentes.
- **Proximidade:** a mais alta no conceito ("explicar o termo quando é dito").
- **Lacunas:** só YouTube/navegador, depende de legendas existentes (não capta áudio), não é app desktop independente.
- Fonte: https://chromewebstore.google.com/detail/aabnfinlckcmaellplkofohhfbaecdda

### 2.2 Subanana — AI Real-time Transcription
- **O que faz:** legendas e tradução ao vivo em dezenas de idiomas, com texto bilíngue lado a lado e **glossário personalizável** para jargões; exporta legendas (ex.: SRT).
- **Lacunas:** serviço web em nuvem; traduz a fala em fluxo contínuo, sem pop-up por termo nem registro de aprendizado.
- Fonte: https://subanana.com/en/ai-real-time-transcription

### 2.3 JotMe
- **O que faz:** tradução em tempo real focada em aulas, com ênfase em tradução contextual de termos técnicos (cita exemplos como "backlog" e "agile"); há app desktop que responde perguntas e gera notas com IA após a aula.
- **Lacunas:** produto comercial em nuvem, orientado a tradução contínua e notas, não a cartões de glossário temporários nem a execução local.
- Fonte: https://www.jotme.io/blog/best-translation-apps-for-students

### 2.4 Soniox App
- **O que faz:** transcrição e tradução em tempo real em mais de 60 idiomas, com rótulos de falante, itens de ação e busca nas transcrições; o fabricante afirma não armazenar áudio nem treinar modelos com ele; plano gratuito inicial.
- **Lacunas:** foco em conversação e mobile; sem glossário de domínio com pop-ups.
- Fonte: https://soniox.com/soniox-app/for/language-students-lecture-transcription

### 2.5 Taskade — Audio to Glossary
- **O que faz:** a partir de gravação ou transcrição, extrai termos, siglas e conceitos e gera glossário alfabetizado com definições baseadas no uso do orador.
- **Lacunas:** processamento posterior (não é em tempo real), sem pop-up.
- Fonte: https://www.taskade.com/convert/audio/audio-to-glossary

### 2.6 Material de apoio conceitual
- Artigo sobre transcrição para estudantes: discute escolher entre tempo real e pré-gravado, e alerta que um termo técnico pode ser reconhecido com confiança e ainda assim errado, o que reforça a necessidade de **viés de vocabulário** e validação. https://smallest.ai/blog/speech-to-text-for-students-turn-lectures-into-notes-and-improve-accessibility
- Nota de pesquisa sobre interação em sala com IA: lista captura de áudio, transcrição de baixa latência e tratamento de vocabulário de domínio como tópicos técnicos centrais. https://hackmd.io/@ll-24-25/ByBXvT0R1x

## 3. Soluções conhecidas, **não verificadas nesta pesquisa**

| Solução | Por que pesquisar depois |
|---|---|
| Language Reactor (extensão) | Legendas duplas e dicionário em pop-up ao passar o mouse; boa referência de UX de dicionário |
| Live Captions (Windows) e Live Caption (Chrome) | Legendas no nível do sistema; verificar suporte a loopback, personalização e privacidade |
| Otter, Notta, Fireflies e similares | Transcrição de reuniões; verificar se oferecem destaque de termos |
| Assistentes embutidos em Zoom/Teams/Meet | Verificar recursos de glossário e legendas traduzidas |
| Apps desktop de ditado local baseados em Whisper | Verificar se algum expõe captura de áudio do sistema e pós-processamento por termos |
| Projetos de código aberto "real-time Whisper" | Úteis como base técnica de captura/segmentação (buscar no GitHub) |

## 4. Matriz comparativa

Legenda: ● sim · ◐ parcial · ○ não · ? não verificado.

| Capacidade | JargonLens | Subanana | JotMe | Soniox | Taskade | **Proposta** |
|---|---|---|---|---|---|---|
| Áudio de qualquer fonte do PC | ○ | ◐ | ● | ○ | ○ | ● |
| Microfone | ○ | ● | ● | ● | ○ | ● |
| Tempo real | ● | ● | ● | ● | ○ | ● |
| Detecção de termos por domínio | ● | ◐ | ◐ | ○ | ● | ● |
| Pop-up/overlay por termo | ● | ○ | ○ | ○ | ○ | ● |
| Glossário personalizável | ○ | ● | ? | ○ | ◐ | ● |
| Escolha de acepção por contexto | ◐ | ? | ◐ | ○ | ◐ | ● |
| Execução local/offline | ◐ | ○ | ○ | ○ | ○ | ● |
| Registro/histórico de aprendizado | ● | ◐ | ◐ | ◐ | ● | ● |
| Desktop standalone | ○ | ○ | ● | ○ | ○ | ● |
| Idioma de saída escolhível | ◐ | ● | ● | ● | ? | ● |

## 5. Lacuna e diferencial

1. **Independência de fonte:** funciona com qualquer aula, call ou vídeo, sem depender de legendas ou da plataforma.
2. **Local primeiro:** privacidade e custo zero no uso básico; nuvem apenas opcional.
3. **Pop-up por termo, não legenda corrida:** reduz carga cognitiva em relação a ler tudo.
4. **Acepção correta:** o exemplo "fairness" (4 sentidos em dicionário geral; em IA, "equidade") mostra o valor de filtrar por domínio.
5. **Escalável por pacotes de domínio:** mesma base para outras áreas.

## 6. Ameaças e competição

- Plataformas de reunião podem lançar glossários nativos.
- Extensões de navegador cobrem bem o caso "vídeo no navegador".
- Mudanças de preço/limites em free tiers de provedores em nuvem.
- Qualidade da transcrição de termos técnicos pode limitar o recall.

## 7. Limites de free tier relevantes (Groq) — verificar na fonte oficial

Fontes secundárias consultadas indicam, para Whisper large-v3 e turbo no plano gratuito: cerca de **20 requisições/min, 2.000/dia, 7.200 s de áudio/hora e 28.800 s/dia**, com cobrança mínima de **10 s por requisição** e uploads limitados a ~25 MB. Os limites são por organização, não por chave. Fontes indicam ainda ausência de garantias de privacidade/SLA no plano gratuito, o que justifica manter o modo local como padrão.

- https://console.groq.com/docs/rate-limits (oficial — confirmar valores atuais)
- https://eesel.ai/blog/groq-pricing
- https://toolfreebie.com/?p=237
- https://spokenly.app/blog/free-speech-to-text-apis
- https://localaimaster.com/blog/groq-api-free-guide

## 8. Perguntas de pesquisa para a próxima rodada

1. Algum projeto de código aberto já combina loopback + Whisper + pós-processamento por glossário?
2. Como Live Captions (Windows) trata áudio do sistema e vocabulário customizado?
3. Quais glossários técnicos abertos e bilíngues existem, e com quais licenças?
4. Qual a latência real de `small.en` em CPUs de notebooks comuns?
5. Existem estudos sobre carga cognitiva de legendas vs. pop-ups de glossário em aprendizagem?
