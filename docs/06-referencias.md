# 06 — Referências e material de apoio

> Links reunidos de pesquisa e conhecimento prévio. **Verifique** versões, licenças e limites nas páginas oficiais antes de usar. Itens marcados com (verificar) não foram abertos durante esta pesquisa.

## 1. Transcrição (STT)

| Recurso | Para quê | Link |
|---|---|---|
| OpenAI Whisper | Modelo original, famílias de modelos (inclui versões somente inglês) | https://github.com/openai/whisper |
| faster-whisper | Implementação otimizada para CPU/GPU, quantização | https://github.com/SYSTRAN/faster-whisper |
| whisper.cpp | Alternativa em C/C++, leve, bom para portar | https://github.com/ggml-org/whisper.cpp (verificar organização atual) |
| Distil-Whisper | Variantes destiladas, mais rápidas | https://github.com/huggingface/distil-whisper |
| Groq — Speech to Text | API opcional (Whisper large-v3 e turbo) | https://console.groq.com/docs/speech-to-text (verificar) |
| Groq — Rate limits | Limites do plano gratuito (fonte oficial) | https://console.groq.com/docs/rate-limits |

**Pontos de atenção:** Whisper não é "streaming" nativo; o tempo real é obtido com segmentação por VAD. Modelos somente inglês tendem a ser menores e mais precisos para áudio em inglês (confirmar no benchmark). O parâmetro de prompt/dica de vocabulário ajuda em termos técnicos.

## 2. Detecção de voz e áudio

| Recurso | Para quê | Link |
|---|---|---|
| Silero VAD | Detecção de fala leve | https://github.com/snakers4/silero-vad |
| PyAudioWPatch | Loopback WASAPI em Python no Windows | https://github.com/s0d3s/PyAudioWPatch |
| Microsoft — Loopback recording | Conceito oficial de captura do áudio de saída | https://learn.microsoft.com/windows/win32/coreaudio/loopback-recording (verificar) |
| BlackHole (macOS) | Dispositivo de áudio virtual | https://github.com/ExistentialAudio/BlackHole (verificar) |
| Apple ScreenCaptureKit | Captura de áudio do sistema no macOS | Buscar "ScreenCaptureKit" na documentação Apple |
| Android AudioPlaybackCapture | Captura de áudio de reprodução com restrições | Buscar "AudioPlaybackCapture" na documentação Android |

## 3. Dados, busca e RAG

| Recurso | Para quê | Link |
|---|---|---|
| SQLite FTS5 | Busca textual de termos e aliases | https://www.sqlite.org/fts5.html |
| sqlite-vec | Busca vetorial dentro do SQLite | https://github.com/asg017/sqlite-vec (verificar estado/licença) |
| pyahocorasick | Casamento rápido de múltiplos termos | https://github.com/WojciechMula/pyahocorasick |
| Sentence-Transformers | Embeddings e documentação de modelos | https://www.sbert.net |
| Modelos de embedding candidatos | `intfloat/multilingual-e5-small`, `BAAI/bge-small-en-v1.5`, `BAAI/bge-m3` | https://huggingface.co (verificar tamanho, licença e desempenho) |

**Pontos de atenção:** como o áudio é em inglês e a saída em português, avalie se o embedding precisa ser multilíngue (acepções em PT) ou se basta embedar as definições/exemplos em inglês e manter PT apenas na apresentação.

## 4. LLM (apenas para exceções)

| Recurso | Para quê | Link |
|---|---|---|
| Ollama | Servidor local de modelos | https://ollama.com (verificar) |
| Hugging Face | Fonte de modelos e documentação | https://huggingface.co/docs |
| Groq — modelos e limites | LLM opcional na nuvem | https://console.groq.com/docs/rate-limits |

**Limites de free tier (fontes secundárias, ago/2026 — verificar):** Whisper large-v3/turbo: ~20 req/min, 2.000 req/dia, 7.200 s de áudio/h, 28.800 s/dia, mínimo de 10 s por requisição; modelos de chat pequenos com milhares de requisições/dia e limites de tokens por minuto. Limites são por organização.

## 5. Interface desktop

| Recurso | Para quê | Link |
|---|---|---|
| Qt for Python (PySide6) | Overlay, bandeja, configurações | https://doc.qt.io/qtforpython-6/ |
| Tauri | Alternativa leve (Rust + web) caso o tamanho do instalador seja crítico | https://tauri.app (verificar) |

**Termos úteis para buscar na documentação de UI:** janela sem borda, sempre no topo, sem ativação ao mostrar, transparente a cliques, bandeja do sistema, atalhos globais, DPI e múltiplos monitores.

## 6. Fontes para glossário (checar licenças!)

| Fonte | Observação |
|---|---|
| Material próprio do curso/residência | Melhor ponto de partida; você controla os direitos |
| Wikipedia / Wikcionário | Conteúdo geralmente sob licença que exige atribuição e compartilhamento igual (CC BY-SA); avaliar impacto na redistribuição |
| Glossários de documentação de projetos open source (ex.: Hugging Face, bibliotecas de ML) | Verificar licença de cada um |
| Glossários de órgãos públicos e normas técnicas | Verificar termos de reutilização |
| Gerar com LLM + revisão humana | Marcar origem como "gerada", revisar antes de promover a curada |

## 7. Legal e ética

- Lei Geral de Proteção de Dados (Lei 13.709/2018): https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm
- Consentimento para gravação/transcrição de reuniões: consultar regras da instituição e das plataformas (Teams, Meet, Zoom).
- Termos de uso de provedores de API (Groq e outros) quanto a retenção e uso de dados.

## 8. Estado da arte — fontes consultadas

- JargonLens: https://chromewebstore.google.com/detail/aabnfinlckcmaellplkofohhfbaecdda
- Subanana: https://subanana.com/en/ai-real-time-transcription
- JotMe: https://www.jotme.io/blog/best-translation-apps-for-students
- Soniox App: https://soniox.com/soniox-app/for/language-students-lecture-transcription
- Taskade audio-to-glossary: https://www.taskade.com/convert/audio/audio-to-glossary
- Transcrição para estudantes: https://smallest.ai/blog/speech-to-text-for-students-turn-lectures-into-notes-and-improve-accessibility
- Notas de pesquisa de IA em sala de aula: https://hackmd.io/@ll-24-25/ByBXvT0R1x
- Limites de Whisper na Groq: https://eesel.ai/blog/groq-pricing · https://toolfreebie.com/?p=237 · https://spokenly.app/blog/free-speech-to-text-apis

## 9. Plano de leitura sugerido

1. Documentação do Whisper e do faster-whisper (modelos, quantização, prompt).
2. Silero VAD e loopback no Windows (entender frames, taxa de amostragem, latência).
3. SQLite FTS5 e sqlite-vec (modelagem do glossário).
4. Documentação de janelas sem foco no framework de UI escolhido.
5. Limites e termos de uso da Groq.
6. Pesquisa complementar das "perguntas de pesquisa" em `03-estado-da-arte.md`.
