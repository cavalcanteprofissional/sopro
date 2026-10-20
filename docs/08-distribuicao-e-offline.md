# 08 — Distribuição e funcionamento offline

Especifica como o Sopro é instalado, como os modelos são obtidos e o que funciona sem
internet. Complementa os requisitos RNF-07 (offline), RNF-08 (instalador e download de
modelos), RNF-09 (áudio não gravado) e RNF-10 (degradação graciosa), e o prompt `A9`.

## 1. Princípios

- **Local primeiro.** Após o download inicial dos modelos, o aplicativo funciona **100%
  offline** no modo local (STT Whisper, glossário em SQLite, embeddings locais).
- **Instalador enxuto.** Os modelos **não** são embutidos no instalador; são baixados **sob
  demanda** na primeira execução (RNF-08).
- **Nuvem é opcional.** Groq (STT/LLM) continua opt-in, com aviso, indicador permanente e
  possibilidade de revogação (RN-04).
- **Sem gravação de áudio.** O áudio fica em memória e é descartado (RNF-09).
- **Só free tier / open source.** Todo modelo distribuído precisa ter licença compatível
  com RNF-12; a licença é registrada por modelo (ver §3).

## 2. O que roda sem internet

| Recurso | Modo local (offline) | Requer internet |
|---|---|---|
| Captura de áudio (loopback/mic) | sim | — |
| VAD e segmentação | sim | — |
| Transcrição (Whisper local) | sim (modelo já baixado) | apenas o download inicial |
| Busca no glossário | sim | — |
| Escolha de acepção (vetorial) | sim (embeddings locais) | — |
| LLM local para exceções | sim (se instalado/baixado) | apenas o download inicial |
| Provedor Groq (STT/LLM) | não | sim (opt-in) |

## 3. Registro de modelos (catálogo)

O aplicativo acompanha um catálogo `data/models.json` que lista os modelos disponíveis e
seus metadados. O núcleo lê o catálogo para saber o que baixar, onde e como verificar.

```json
{
  "registry_version": 1,
  "models": [
    {
      "id": "whisper-small-en",
      "kind": "stt",
      "engine": "faster-whisper",
      "name": "Whisper small.en",
      "languages": ["en"],
      "output_langs": ["pt-BR"],
      "license": "MIT",
      "size_bytes": 0,
      "verified": false,
      "files": [
        {
          "path": "model.bin",
          "url": "https://huggingface.co/.../model.bin",
          "sha256": "",
          "size_bytes": 0
        }
      ],
      "notes": "Placeholder; preencher url/sha256/tamanho e marcar verified=true."
    }
  ]
}
```

### Campos

| Campo | Regra |
|---|---|
| `id` | Identificador único e estável (usado no cache local). |
| `kind` | `stt`, `embedding` ou `llm`. |
| `engine` | Implementação pretendida (ex.: `faster-whisper`, `whisper.cpp`, `sentence-transformers`). |
| `license` | Licença do modelo; obrigatória para distribuição (RNF-12). |
| `verified` | `true` só depois de conferir url, `sha256`, tamanho e licença na fonte oficial. |
| `files[]` | Um ou mais artefatos; cada um com `url`, `sha256` e tamanho. |
| `sha256` | Hash do arquivo; **obrigatório** para baixar (itens sem hash ficam bloqueados). |

> Itens com `verified=false` ou `sha256` vazio servem de **modelo/template** e não são
> baixados automaticamente. Preencher na curadoria (prompt `A9`).

## 4. Fluxo de download sob demanda

1. Na primeira execução, a tela inicial pergunta domínio, idioma de saída e fontes de áudio.
2. O aplicativo cria a pasta de dados/cache (§5) e baixa os modelos marcados como
   necessários (ex.: o modelo de STT ativo) fora da thread da UI. O progresso aparece no
   **indicador de estado** (estado `Carregando…` com a fração baixada) e na bandeja, sem
   diálogo modal bloqueante.
3. Cada arquivo é baixado para um `.tmp` e **verificado por sha256** antes de ser promovido
   ao caminho final. Arquivo inválido é descartado e o download pode ser repetido.
4. Se a rede falhar ou o download/warmup do modelo falhar, o app entra no estado `ERROR`
   (indicador e bandeja), mantém o que já baixou e oferece **"Tentar de novo"** na bandeja; a
   bandeja continua viva e nada mais é bloqueado (RNF-10).
5. Depois de baixado, o modelo é reutilizado sem nova verificação de rede (checagem de hash
   é opcional a cada uso).

## 5. Cache e caminhos

Pasta de dados do aplicativo, resolvida nesta ordem:

1. Variável de ambiente `SOPRO_HOME` (útil em testes e instalações portáteis).
2. Padrão do usuário: `~/.sopro` (o instalador pode apontar para `%LOCALAPPDATA%\Sopro`).

Layout:

```
<SOPRO_HOME>/
  models/<model_id>/        arquivos dos modelos baixados
  sopro.db                  banco SQLite (histórico, cache, configurações)
  sopro.db-wal / -shm       journal WAL (conexões por thread)
  sopro.lock                trava de instância única (app principal)
  sopro-demo.lock           trava separada do modo --demo
  logs/                     logs sem conteúdo de fala
```

## 6. Modelos previstos

| Uso | Candidatos | Licença | Observação |
|---|---|---|---|
| STT local | Whisper `small.en` / variante destilada (faster-whisper ou whisper.cpp) | MIT | Escolhido por benchmark (Fase 0/1). |
| Embeddings (RAG) | `intfloat/multilingual-e5-small`, `BAAI/bge-small-en-v1.5`, `BAAI/bge-m3` | verificar por modelo | Avaliar multilíngue vs. inglês (docs/06 §3). |
| LLM (exceções) | modelo local pequeno via servidor compatível com API de chat | verificar | Decisão em aberto (docs/02 §13.2). |

> Confirmar url, tamanho, hash e licença de cada modelo na fonte oficial antes de
> `verified=true` (itens marcados **(verificar)**).

## 7. Integridade e segurança

- Hash **sha256** obrigatório para todo download; comparação em streaming, sem carregar o
  arquivo inteiro em memória.
- Downloads por HTTPS; nunca executar conteúdo baixado.
- Chaves de API (quando houver) ficam no cofre de credenciais do SO, nunca no catálogo nem
  em logs.
- O catálogo não contém credenciais.

## 7.1 Concorrência local (banco e instâncias)

- O banco em arquivo usa **uma conexão por thread** (`threading.local`), em modo WAL e com
  `busy_timeout`, permitindo que a thread de áudio grave detecções enquanto a UI lê o
  histórico. Bancos `:memory:` (testes) compartilham a conexão sob um `RLock`.
- Uma **trava de instância única** (`QLockFile` em `%LOCALAPPDATA%\Sopro`) impede bandejas
  duplicadas disputando o mesmo banco. A segunda execução sinaliza a instância existente por
  um `QLocalServer` (que traz o hub para frente) e encerra sem abrir banco ou carregar modelo.
- `--demo` usa um canal e uma trava próprios: roda em paralelo ao app real, mas não duplicado.

## 8. Relação com os requisitos

| Requisito | Como este documento atende |
|---|---|
| RNF-07 (offline) | §2 e §4: offline após o download inicial. |
| RNF-08 (instalador + modelos no 1º uso) | §1, §3 e §4: instalador enxuto, catálogo e download verificado. |
| RNF-09 (sem gravar áudio) | §2: áudio só em memória. |
| RNF-10 (degradação graciosa) | §4 passo 4. |
| RNF-12 (free tier/open source) | §3 e §6: licença obrigatória por modelo. |
| RN-04 (indicador de nuvem) | §2 e §1. |
