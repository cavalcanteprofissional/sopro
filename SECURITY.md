# Política de Segurança e Privacidade

O Sopro foi desenhado com **privacidade em primeiro lugar**. Esta política descreve os
compromissos e como reportar problemas.

## Princípios de privacidade

- **Local por padrão:** o áudio é processado na máquina do usuário. O modo local funciona
  100% offline após o download dos modelos (RNF-07).
- **Áudio não é gravado em disco por padrão:** os frames ficam em memória e são descartados
  após a transcrição (RNF-09).
- **Sem telemetria:** dados de uso não são enviados para analytics ou terceiros não
  relacionados à conta (RN-05).
- **Nuvem de IA é opcional:** provedores em nuvem (ex.: Groq) exigem opt-in explícito, com
  aviso, indicador permanente na bandeja e possibilidade de revogar a qualquer momento
  (RN-04).
- **Conta e dados em nuvem (Fase 7 planejada):** histórico, configurações e glossários vão
  para Clerk/Neon/R2, isolados por `user_id`. Tokens ficam no cofre do SO. Áudio continua
  **nunca** sendo enviado.
- **Logs sem conteúdo de fala:** as chaves de API nunca aparecem em texto puro nos logs.
- **Contexto opcional:** o `context_snippet` das detecções fica desligado por padrão.

## Escopo de segurança

Áreas consideradas no modelo de ameaça:

- Captura de áudio de saída (loopback) e de microfone no Windows.
- Armazenamento local de configurações e chaves (preferencialmente no cofre de credenciais
  do SO).
- Comunicação com provedores de IA em nuvem quando ativados explicitamente.
- Fase 7 planejada: autenticação Clerk, API Worker, Neon e R2; isolamento por usuário,
  validação de JWT, URLs assinadas e backup de 30 dias.
- Importação de pacotes de domínio (JSON/CSV) de terceiros.

## Versões suportadas

Projeto em fase de protótipo; correções de segurança serão aplicadas na branch principal.

## Reportando uma vulnerabilidade

**Não abra uma issue pública para problemas de segurança.**

Reporte de forma privada aos mantenedores do projeto (canal a definir) incluindo:

1. Descrição do problema e impacto potencial.
2. Passos para reproduzir (sem dados sensíveis ou conteúdo de fala).
3. Versão/commit afetado e ambiente (SO, versão do Python).
4. Se possível, uma sugestão de correção.

Você receberá uma resposta confirmando o recebimento e o andamento. Pedimos que aguarde a
correção antes de qualquer divulgação pública (divulgação responsável).

## Conformidade e uso responsável

- Gravar ou transcrever reuniões pode exigir **consentimento dos participantes** e está
  sujeito à LGPD (Lei 13.709/2018). O app exibe aviso na primeira execução.
- Respeite os termos de uso das plataformas de reunião e das instituições de ensino.
- Verifique as licenças das fontes de glossário antes de redistribuí-las
  (ver [docs/06-referencias.md](docs/06-referencias.md)).
