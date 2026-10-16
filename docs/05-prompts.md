# 05 — Prompts

Dois grupos:
- **A. Prompts de desenvolvimento**: para colar em um assistente de código, um por fase.
- **B. Prompts de runtime**: usados pelo próprio app (LLM e Whisper).

Substitua `{{variáveis}}`. Cole sempre o **Prompt-mestre** no início de cada sessão e anexe os arquivos `01` e `02`.

---

## A. Prompts de desenvolvimento

### A0. Prompt-mestre (contexto fixo)

```
Você é um engenheiro de software sênior ajudando a construir um aplicativo desktop
chamado "{{nome_provisório}}".

PRODUTO
Escuta o áudio de aulas/calls (saída do computador e/ou microfone), transcreve em tempo
real em inglês, detecta termos técnicos de um domínio (inicialmente tecnologia) e mostra
um pop-up temporário estilo dicionário com o termo em inglês e a tradução/definição no
idioma escolhido (padrão pt-BR). Registra detecções em SQLite local.

RESTRIÇÕES
- Windows no protótipo; núcleo independente de SO para portar depois (Linux, macOS, mobile).
- Standalone, leve, local por padrão. Groq é opcional (STT e LLM) e deve exigir aviso.
- Somente free tier e software livre/gratuito.
- Áudio não é gravado em disco por padrão. Sem telemetria.
- O LLM NÃO processa toda frase: caminho rápido = busca em glossário local.

DOCUMENTOS
Siga os requisitos (RF/RNF/RN) em 01 e a arquitetura/contratos em 02. Se algo conflitar
ou faltar, liste as dúvidas antes de codificar.

REGRAS DE TRABALHO
1. Antes de escrever código, resuma o que vai fazer e os arquivos que criará/alterará.
2. Entregue em passos pequenos e testáveis; inclua como executar e como testar.
3. Escreva testes para a lógica do núcleo (matcher, resolvedor de acepção, repositório).
4. Não adicione dependências pesadas sem justificar tamanho e licença.
5. Trate erros de rede/provedor com degradação graciosa.
6. Não invente APIs: se não tiver certeza de uma assinatura, diga e peça para verificar a
   documentação.
7. Ao final, liste riscos, pendências e o próximo passo.
```

### A1. Fase 0 — Glossário seed e conjunto de teste

```
Com base no formato de 07-glossario-seed-modelo.md, gere 50 entradas de glossário de
tecnologia/IA em JSON (campos: canonical_en, pos, aliases, priority, is_ambiguous e
senses[] com ordinal, domain_tag, translation_pt, definition_pt curta, register, example_en).
Regras:
- Definições em até 25 palavras, em português do Brasil, corretas e neutras.
- Para termos polissêmicos (ex.: fairness, bias, model, token, layer, kernel, pipeline),
  inclua TODAS as acepções relevantes e marque a de tecnologia/IA com domain_tag="tech".
- Não invente siglas; se tiver dúvida sobre um termo, coloque-o em uma lista "revisar".
- Sinalize quais termos são palavras muito comuns (candidatos à stoplist).
Em seguida, proponha um template CSV para anotar áudios de teste:
inicio_s, fim_s, termo_canonico, acepcao_esperada.
```

### A2. Fase 1 — Captura de áudio (Windows)

```
Implemente o módulo `audio` para Windows:
- Listar dispositivos de entrada e de saída (loopback).
- Abrir um stream de loopback e um de microfone simultâneos, convertendo para PCM 16 kHz
  mono, frames de 20–30 ms, entregues por fila com etiqueta de fonte ("system"/"mic").
- Tratar troca de dispositivo padrão, dispositivo desconectado e taxa de amostragem diferente.
- Interface abstrata `AudioSource` para outras plataformas no futuro.
Entregue: código, um script de teste que grava 10 s apenas em memória e imprime nível RMS
por fonte, e uma lista de armadilhas conhecidas de loopback no Windows. Não use
armazenamento em disco do áudio.
```

### A3. Fase 1 — VAD e STT

```
Implemente `vad` e `stt`:
- VAD que forma segmentos de fala (limite máximo configurável 8–12 s, sobreposição 0,3–0,5 s).
- Interface STTProvider (warmup, transcribe, close) conforme 02, com implementação local
  baseada em Whisper somente inglês, quantizado para CPU.
- Suporte a dica de vocabulário (lista de termos do glossário, truncada ao limite do modelo).
- Medição de tempo por etapa (captura→VAD→STT) em log estruturado.
Entregue testes com arquivos de áudio curtos e um modo benchmark que compara a saída com
a anotação CSV e calcula recall e precisão de termos. Não implemente o provedor Groq ainda.
```

### A4. Fase 1 — Matcher

```
Implemente `matcher` conforme a seção 4 de 02:
- Normalização, n-gramas de 1 a 4 tokens, maior casamento primeiro.
- Aliases e flexões simples; stoplist com regra de contexto para termos comuns.
- Cooldown por termo e orçamento de pop-ups por minuto.
- Estrutura eficiente (por exemplo, autômato ou índice em memória) com carga a partir do SQLite.
Entregue testes de unidade cobrindo: termos de várias palavras, plural, sigla, falso
positivo de palavra comum, cooldown e orçamento. Documente a complexidade.
```

### A5. Fase 2 — Overlay (pop-up)

```
Implemente `popup` para Windows seguindo a seção 8 de 02:
- Janela sem borda, sempre no topo, que NÃO recebe foco nem ativa ao aparecer.
- Cartão com termo em destaque, classe, acepções numeradas (relevante em destaque),
  rótulo de registro (ex.: arcaico) e origem (glossário/gerado).
- Fila com máximo N cartões, auto-fechamento, pausa no hover, clique fecha, ação "fixar".
- Posição configurável, múltiplos monitores, DPI alto, tema claro/escuro.
Entregue um modo de demonstração que dispara pop-ups fictícios e um roteiro de teste manual
(30 min com Teams/Meet/Zoom aberto) para provar que o foco não é roubado.
```

### A6. Fase 2 — Persistência e configurações

```
Implemente `repo` e `config` com SQLite conforme o modelo de dados de 02:
- Migrações versionadas, índices FTS5 para termos/aliases.
- Tabelas de sessão e detecção (context_snippet opcional e desligado por padrão).
- Exportação do histórico em CSV e Markdown.
- Configurações com validação; chaves de API no cofre de credenciais do SO quando possível.
Entregue testes de migração e de exportação.
```

### A7. Fase 3 — RAG e acepções

```
Implemente `rag` e `SenseResolver`:
- Embeddings locais para cada acepção (modelo pequeno multilíngue, a justificar), armazenados
  em índice vetorial no SQLite.
- Cascata: acepção única → domain_tag → similaridade vetorial (limiar configurável) → LLM.
- Janela de contexto = últimos N segundos de texto transcrito.
- Caminho para termos fora do glossário: LLMProvider (local; Groq opcional) usando o prompt
  B1, saída em JSON validada, cache e fila de aprovação.
Entregue um conjunto de casos ambíguos (fairness, bias, model, token, kernel, pipeline) com
frases de teste e a acepção esperada, e meça acurácia.
```

### A8. Fase 3 — Provedor Groq opcional

```
Implemente GroqSTT e GroqLLM atrás das interfaces existentes:
- Ativação somente após aviso de privacidade e confirmação do usuário; indicador na bandeja.
- Respeitar limites do plano gratuito (requisições/min, requisições/dia, segundos de áudio/h),
  com backoff e retorno automático ao provedor local em caso de erro/limite.
- Agrupar segmentos para respeitar o mínimo de ~10 s por requisição.
- Verifique limites atuais na documentação oficial antes de fixar números no código.
Entregue testes com respostas simuladas (limite excedido, timeout, rede ausente).
```

### A9. Fase 4 — Empacotamento

```
Prepare a distribuição para Windows:
- Empacotamento do app em executável com instalador.
- Download de modelos no primeiro uso, com verificação de integridade e barra de progresso.
- Tela de primeira execução: consentimento (LGPD/uso em reuniões), domínio, idioma de saída,
  fontes de áudio.
- Estimativa de tamanho do instalador e dos modelos, e plano para reduzi-lo.
Entregue checklist de teste em máquina limpa.
```

### A10. Revisão de segurança e privacidade

```
Revise o projeto contra RNF-07, RNF-09 e a seção 10 de 02. Verifique: se algum áudio ou
texto de fala é gravado em disco ou em logs; se chaves aparecem em texto puro; se o modo
nuvem exige aviso; se há chamadas de rede inesperadas no modo local. Liste achados por
severidade com correção sugerida.
```

---

## B. Prompts de runtime (usados pelo app)

### B1. LLM — definição e escolha de acepção (saída em JSON)

**Sistema:**
```
Você é um assistente de glossário técnico. Responda SOMENTE com JSON válido, sem texto
extra e sem blocos de código.

Tarefa: dado um termo em inglês ouvido em uma aula, o domínio ativo, o idioma de saída e
o contexto recente, escolha o significado correto para o domínio e gere uma explicação curta.

Esquema:
{
  "term": string,
  "in_glossary": boolean,
  "chosen_sense_id": string | null,
  "translation": string,
  "definition": string,       // até 25 palavras, no idioma de saída
  "confidence": number,       // 0 a 1
  "generated": boolean        // true se não veio do glossário
}

Regras:
- Use apenas as acepções fornecidas quando houver; escolha a mais coerente com o domínio
  e o contexto.
- Se o termo não estiver no glossário, gere definição curta e marque generated=true.
- Se não tiver certeza, use confidence baixa; NÃO invente fatos, siglas ou fontes.
- Não repita o contexto; não adicione opiniões; mantenha tom neutro.
```

**Usuário (template):**
```
domínio: {{domínio}}
idioma_de_saída: {{idioma}}
termo_ouvido: {{termo}}
contexto_recente: """{{últimos_N_segundos_de_texto}}"""
acepcoes_candidatas: {{lista_json_de_acepções_ou_vazia}}
```

### B2. LLM — expansão de glossário (curadoria offline)

```
Gere entradas de glossário no formato de 07-glossario-seed-modelo.md para os termos:
{{lista_de_termos}}
Domínio: {{domínio}}. Idioma de saída: {{idioma}}.
Regras: definições de até 25 palavras; inclua todas as acepções relevantes de dicionário
geral e marque a do domínio; liste aliases (plural, sigla); marque "revisar" nos termos
sobre os quais você tem dúvida. Responda apenas com JSON.
```

### B3. Dica de vocabulário para o Whisper

Regra de montagem (não é prompt de LLM, é texto passado ao STT):
```
Montagem: concatenar termos de maior prioridade do domínio, separados por vírgula, em frase
natural curta, respeitando o limite de tokens do modelo.
Exemplo: "Technical lecture on machine learning: overfitting, gradient descent, fairness,
embeddings, transformer, fine-tuning, inference, tokenization."
Dinâmica: priorizar termos ainda não vistos na sessão e termos de alta prioridade; truncar
no limite; regenerar a cada alguns minutos conforme o assunto muda.
```

### B4. Verificação de acepção (checagem de qualidade, opcional)

```
Dado o trecho abaixo e as acepções numeradas do termo "{{termo}}", responda com apenas o
número da acepção mais adequada ao domínio {{domínio}}, ou 0 se nenhuma servir.
Trecho: """{{contexto}}"""
Acepções: {{lista_numerada}}
```

---

## C. Boas práticas ao usar estes prompts

- Peça **planos antes de código** e **testes junto com código**.
- Cole os requisitos exatos (RF/RNF) referentes à fase, não o documento inteiro, quando o contexto ficar longo.
- Peça ao assistente que cite a documentação oficial das bibliotecas e que sinalize incertezas sobre assinaturas de API.
- Revise manualmente definições geradas por LLM antes de promovê-las a glossário curado.
