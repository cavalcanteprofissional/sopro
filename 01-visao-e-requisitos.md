# 01 — Visão e requisitos

## 1. Problema

Estudantes e profissionais brasileiros acompanham aulas, palestras e calls técnicas em inglês. Termos especializados ("fairness", "overfitting", "backlog") passam rápido; parar para pesquisar quebra a atenção, e legendas automáticas não explicam o termo nem escolhem o sentido correto para a área.

## 2. Visão

Um companheiro discreto que, **no momento em que o termo é falado**, mostra um cartão curto com o termo, a tradução e a definição no contexto da área, sem interromper a aula e sem enviar dados para fora (por padrão).

## 3. Público e cenários

| Persona | Cenário |
|---|---|
| Estudante de pós/residência em IA | Aula ao vivo em inglês no Teams/Meet/Zoom |
| Profissional de TI | Reunião técnica com colegas estrangeiros |
| Autodidata | Curso gravado no YouTube/Udemy tocando no computador |
| Fase 2 (futuro) | Profissionais de outras áreas (direito, saúde, finanças) via pacotes de domínio |

## 4. Requisitos funcionais

### Captura de áudio
- **RF-01** Capturar o áudio de **saída** do sistema (loopback) no Windows.
- **RF-02** Capturar o áudio de **entrada** (microfone).
- **RF-03** O usuário escolhe: só saída, só entrada ou ambas; escolhe também o dispositivo específico.
- **RF-04** Cada fonte carrega uma etiqueta (`system` / `mic`) que acompanha o texto transcrito.

### Transcrição
- **RF-05** Transcrever em tempo real (segmentos curtos) em inglês, com modelo local.
- **RF-06** Prover um segundo provedor opcional (Groq Whisper), selecionável nas configurações.
- **RF-07** Ao ativar o provedor em nuvem, exibir aviso explícito de que o áudio sai da máquina e exigir confirmação.
- **RF-08** Usar os termos do glossário ativo como dica de vocabulário (prompt) para o modelo de transcrição.

### Detecção e filtro de domínio
- **RF-09** Detectar no texto transcrito os termos presentes no glossário do **domínio ativo** (inicialmente "tecnologia").
- **RF-10** Suportar termos de várias palavras (ex.: "gradient descent") e variações (plural, flexões, siglas, sinônimos/aliases).
- **RF-11** Ignorar palavras comuns que coincidem com termos (lista de exclusão e regras de contexto).
- **RF-12** Permitir ativar mais de um domínio e trocar de domínio sem reinstalar (pacotes de domínio).

### Definição contextual (RAG)
- **RF-13** Para termos com várias acepções, escolher a acepção mais adequada ao contexto usando recuperação semântica sobre o glossário e o texto recente.
- **RF-14** Para termo candidato **fora** do glossário, gerar definição curta via LLM (local por padrão; Groq opcional), marcando-a como "gerada" e guardando em cache.
- **RF-15** A saída (tradução/definição) respeita o idioma de saída escolhido.

### Pop-up
- **RF-16** Exibir pop-up temporário, sem borda, sempre no topo, **sem roubar o foco** da janela atual.
- **RF-17** Conteúdo: termo (destaque), classe gramatical/tipo, tradução, definição curta numerada por acepção (apenas a acepção relevante em destaque), etiqueta de origem (glossário/gerado).
- **RF-18** Fechar automaticamente após tempo configurável; fechar por clique; fixar (impedir fechamento) por ação do usuário.
- **RF-19** Evitar repetição: cooldown por termo e limite de pop-ups por minuto, configuráveis.
- **RF-20** Empilhar pop-ups simultâneos de forma legível (máximo configurável).

### Persistência
- **RF-21** Registrar em banco local cada detecção: termo, acepção escolhida, horário, sessão, fonte do áudio, trecho de contexto (opcional).
- **RF-22** Tela de histórico/revisão: buscar, filtrar por sessão, marcar como "aprendido", exportar (CSV/Markdown).
- **RF-23** Gerenciar glossários: importar/exportar pacotes de domínio, editar entradas e adicionar termos manualmente.

### Configuração e utilidade
- **RF-24** Idioma de saída selecionável (padrão pt-BR); arquitetura preparada para novas línguas.
- **RF-25** Atalhos globais: pausar/retomar escuta, mostrar/ocultar histórico.
- **RF-26** Ícone na bandeja do sistema com estado (escutando / pausado / erro).

## 5. Requisitos não funcionais

| ID | Requisito | Meta inicial (calibrar) |
|---|---|---|
| RNF-01 | Latência do fim da fala até o pop-up | P95 ≤ 3 s (termo do glossário, STT local) |
| RNF-02 | Recall de detecção em conjunto anotado | ≥ 85% |
| RNF-03 | Precisão dos pop-ups | ≥ 90% relevantes |
| RNF-04 | Pop-ups falsos ou irrelevantes | ≤ 2 por minuto |
| RNF-05 | Uso de CPU durante uma call (máquina de referência a definir) | média ≤ 30% |
| RNF-06 | Uso de RAM | ≤ 2 GB com modelos carregados |
| RNF-07 | Funcionar 100% offline no modo local (após baixar modelos) | Obrigatório |
| RNF-08 | Instalador simples; modelos baixados no primeiro uso | Obrigatório |
| RNF-09 | Áudio **não** é gravado em disco por padrão | Obrigatório |
| RNF-10 | Falha de rede/provedor não derruba o app (degradação graciosa) | Obrigatório |
| RNF-11 | Código separado em núcleo (independente de SO) e camadas de plataforma | Obrigatório |
| RNF-12 | Somente free tier e software livre ou gratuito | Obrigatório |

## 6. Regras de negócio

- **RN-01** Um termo só dispara pop-up se pertencer a um domínio ativo.
- **RN-02** O mesmo termo não reaparece dentro do cooldown (padrão 120 s), salvo se o usuário desativar.
- **RN-03** Entradas geradas por LLM são visualmente distinguíveis das curadas.
- **RN-04** Se o provedor em nuvem estiver ativo, mostrar indicador permanente na bandeja.
- **RN-05** Dados de uso nunca são enviados a terceiros; apenas o áudio/texto estritamente necessário ao provedor escolhido pelo usuário.

## 7. Fora de escopo (protótipo)

- Versões macOS, Linux e mobile (apenas preparar a arquitetura).
- Diarização de falantes, resumos de aula, geração de notas.
- Transcrição de idiomas diferentes de inglês.
- Sincronização na nuvem e contas de usuário.
- Tradução da fala inteira (o foco é o termo, não a legenda).

## 8. Critérios de aceite do protótipo

1. Em 3 aulas reais de 10 min em inglês sobre IA/tecnologia, os requisitos RNF-01 a RNF-04 são atingidos ou os desvios são documentados.
2. O app roda sem internet no modo local.
3. O pop-up não rouba foco do Teams/Meet/Zoom durante 30 min de teste.
4. O histórico exporta corretamente em CSV.
5. A troca de idioma de saída funciona sem reiniciar.

## 9. Considerações legais e éticas

- Gravar ou transcrever chamadas pode exigir **consentimento dos participantes** e se sujeita à LGPD (Lei 13.709/2018). Incluir aviso na primeira execução e opção de não armazenar contexto.
- Respeitar termos de uso das plataformas de reunião e das instituições de ensino.
- Verificar licenças das fontes de glossário (ver `06-referencias.md`).
