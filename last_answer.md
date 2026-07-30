# Clarificação — Decisões consolidadas para correção do fallback Vimeo

## 1. Ambiguidades encontradas
- **A1 (mecanismo de classificação sob `ignoreerrors=True`)** — resolvida por D1.
- **A2 (quando classificar `format_unavailable`)** — resolvida por D2.
- **A3 (manter ou remover fallback Python)** — resolvida por D3.
- **A4 (ordem de tentativas no loop)** — não abordada; recomenda-se manter a ordem atual.
- **A5 (constante vs. inline)** — resolvida por D4.
- **A6 (interação D1 com fallback existente)** — tornou-se irrelevante com D3.
- **A7 (escopo do pre-flight)** — tornou-se irrelevante com o seletor RF1 (já encadeia `best` nativamente).

## 2. Decisões necessárias (consolidadas)

### D1 — `ignoreerrors` no pre-flight ✅ **aprovado**
- Pre-flight (`extract_info(download=False)`): `preflight_opts = {**ydl_opts, "ignoreerrors": False}`.
- Download real (`_download`): manter `ydl_opts` original com `ignoreerrors=True`.

### D2 — Classificação de erro ✅ **definido**
- Centralizar classificação em `_classify_error` (função já existe em `get_video.py:5-15`).
- No pre-flight: qualquer `DownloadError` → classificar e **retornar imediatamente**, sem iniciar download real.
- No download real: classificar erros que só ocorram após o pre-flight.
- **Log emitido uma única vez pelo chamador** (`process_smart_batch` em `main.py`), evitando duplicidade.

### D3 — Fallback Python ✅ **remover**
- Remover o bloco `if bucket == "format_unavailable": ... fallback ...` de `get_video.py:66-75`.
- Manter apenas `ydl_opts.setdefault('format', 'best')` em `get_video.py:44` como **default defensivo** para chamadores que não forneçam `format` (não é a política do `process_smart_batch`).

### D4 — Seletor de formato ✅ **inline em main.py**
- Manter seletor inline em `main.py:116` com o valor exato de RF1.
- Nenhum import cruzado entre `main.py` e `get_video.py` neste hotfix.
- Remover de `get_video.py` qualquer vestígio de política duplicada de formato.

### D5 — Política de log (derivada de D2)
- Pre-flight: **silencioso** (nenhuma saída em sucesso ou falha).
- Chamador (`main.py:process_smart_batch`): imprime `⚠️ [bucket] Falha: {url}` uma única vez por tentativa.
- Sucesso: `✅ [{bucket}] Download concluído: {unique_title}` (já existe).
- Pré-tentativa: `🔄 Tentando: ...` (já existe).

## 3. Riscos se seguir sem esclarecer (todos endereçados)
- **R1** — Aplicar D1 sem resolver A6: eliminado por D3 (fallback removido).
- **R2** — Código morto em `get_video.py:66-75`: eliminado por D3.
- **R3** — Diff maior que o mínimo: aceito; D3 + D4 produzem diff contido.
- **R4** — Seletor espalhado: mitigado por D4 (inline, sem duplicação).
- **R5** — Log duplicado: eliminado por D2 (log único pelo chamador).

## 4. Perguntas obrigatórias (respondidas)
| Q | Decisão | Resposta |
|---|---------|----------|
| Q1 — D1: ignoreerrors=False no pre-flight? | Sim | ✅ `{**ydl_opts, "ignoreerrors": False}` no pre-flight; `True` no download |
| Q2 — D2: onde classificar? | Ambos os caminhos | Pre-flight: retorno imediato. Download real: erros pós-pre-flight. Log único pelo chamador |
| Q3 — D3: manter ou remover fallback Python? | Remover | Bloco `if bucket == "format_unavailable"` removido. `setdefault('format','best')` mantido como default defensivo |
| Q4 — D4: inline ou constante? | Inline | Seletor RF1 inline em `main.py:116`. Sem import cruzado |

## 5. Perguntas opcionais (não abordadas)
- **Q5** — Ordem do loop: manter a atual (URL wrapper primeiro, `player.vimeo.com` depois).
- **Q6** — A6/A7 tratadas como irrelevantes com D3 + RF1.
- **Q7** — Granularidade do log: uma linha por tentativa, conforme D2.

## 6. Suposições seguras
- Endpoint HTTP continua respondendo 200 OK com `{message: string}` (C3).
- Buckets mantêm nome e semântica (C5): `format_unavailable`, `embed_only`, `unsupported`, `other`, `ok`, `ok_fallback`.
- Nenhum arquivo fora de `backend/app/main.py` e `backend/app/get_video.py` é modificado (C4).
- Cookies, `Referer`, `User-Agent` e `_pick_embed_referer` permanecem inalterados.
- A URL de teste permanece `https://tiexames.com.br/novoensino/vimeo/player.php?SESSAO=3281` (e a interna `https://player.vimeo.com/video/1210147270`).

## 7. Próxima etapa recomendada
Carregar a skill `plan` para detalhar a implementação das edições:

1. **`backend/app/main.py:116`** — substituir seletor por RF1.
2. **`backend/app/get_video.py`**:
   - Manter `_classify_error` como função centralizada (sem mudança de assinatura).
   - Refatorar `download_video_with_class` para usar `preflight_opts` com `ignoreerrors=False` no `extract_info`; retornar imediatamente em caso de `DownloadError`/`ExtractorError`.
   - Manter `_download` com `ydl_opts` original.
   - Remover o bloco de fallback Python (`get_video.py:66-75`).
   - Preservar `setdefault('format', 'best')` como default defensivo.
3. Lista de smoke tests manuais (YouTube/m3u8 + Vimeo 1210147270).

---

## Resumo da sessão

**Solicitação original**: o usuário invocou `/clarify` com o problema e propôs D1 para resolver as ambiguidades A1, A2, A3 e A5 da especificação anterior, solicitando que apenas ambiguidades, decisões e perguntas fossem listadas.

**Produto**: clarificação com 7 seções detalhando 7 ambiguidades (A1–A7, das quais 3 resolvidas, 2 irrelevantes, 1 não abordada), 5 decisões consolidadas (D1–D5), 5 riscos endereçados, 4 perguntas obrigatórias respondidas (todas as opções recomendadas), e próxima etapa (plan).

**Modo de operação**: clarify — nenhum arquivo foi alterado.
