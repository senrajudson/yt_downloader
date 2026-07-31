# Plano técnico — Correção incremental do fallback de formato Vimeo

## 1. Objetivo técnico
Corrigir o download do vídeo Vimeo `1210147270` (incorporado em `https://tiexames.com.br/novoensino/vimeo/player.php?SESSAO=3281`) substituindo o seletor rígido de 360p por um seletor encadeado com fallback nativo e ajustando a classificação de erros para que o bucket `format_unavailable` seja emitido sob `ignoreerrors=True`. A correção deve ser mínima, localizada em `backend/app/main.py` e `backend/app/get_video.py`, e preservar o restante do comportamento atual.

## 2. Estratégia proposta
- **2.1 Substituição do seletor (RF1)** — trocar a string em `main.py:116` pelo bloco exato:
  ```python
  'format': (
      "bestvideo*[height<=360]+bestaudio/"
      "best[height<=360]/"
      "bestvideo*+bestaudio/"
      "best"
  )
  ```
- **2.2 Pre-flight com `ignoreerrors=False` (D1)** — dentro de `download_video_with_class`, criar `preflight_opts = {**ydl_opts, "ignoreerrors": False}` e usar somente no `extract_info(download=False)`. Manter `ydl_opts` original (com `ignoreerrors=True`) no `_download`.
- **2.3 Retorno imediato no pre-flight (D2)** — se o pre-flight lançar `DownloadError` ou `ExtractorError`, classificar via `_classify_error` e retornar `(False, bucket)` antes de iniciar o download real.
- **2.4 Classificação centralizada** — `_classify_error` permanece como single source of truth (já existe em `get_video.py:5-15`); o `if not info: return (False, "other")` em `get_video.py:50` é substituído pelo caminho classificado.
- **2.5 Remoção do fallback Python (D3)** — apagar o bloco `if bucket == "format_unavailable": ... fallback_opts = {**ydl_opts, 'format': 'best'} ...` em `get_video.py:66-75`. Preservar `ydl_opts.setdefault('format', 'best')` em `get_video.py:44` como default defensivo.
- **2.6 Log único pelo chamador (D5)** — `process_smart_batch` em `main.py` já emite `⚠️ [bucket] Falha: {url}` e `✅ [{bucket}] Download concluído: ...`; nenhuma duplicação deve ocorrer porque o pre-flight é silencioso e `_download` não imprime mais nada além do já delegado.
- **2.7 Inline sem cruzamento de imports (D4)** — seletor permanece inline em `main.py:116`; nenhuma constante é exportada de `get_video.py` nem importada em `main.py`.

## 3. Arquivos provavelmente impactados
- `backend/app/main.py` — única edição: linha 116 (seletor).
- `backend/app/get_video.py` — edições em:
  - `_classify_error` (sem mudança de assinatura; apenas garantir uso nos dois caminhos).
  - `download_video_with_class` (pre-flight com `ignoreerrors=False`, retorno imediato, fim do fallback Python).
  - `_download` (sem mudança funcional; apenas remover impressões duplicadas, se houver).

**Não editados**: `extension/*`, `backend/app/utils.py`, `backend/scripts/*`, `data.json`, `AGENTS.md`, `__initi__.py`, `pyproject.toml`, `backend/app/main.py` exceto linha 116.

## 4. Alteração prevista por arquivo

### 4.1 `backend/app/main.py`
- **Linha 116** — substituir:
  ```python
  'format': 'best[height=360]/bestvideo[height=360]+bestaudio/best[height<=360]',
  ```
  por:
  ```python
  'format': (
      "bestvideo*[height<=360]+bestaudio/"
      "best[height<=360]/"
      "bestvideo*+bestaudio/"
      "best"
  ),
  ```
- Nenhuma outra linha é alterada. Em particular, `_pick_embed_referer`, injeção de `http_headers` em `main.py:120-130`, `time.sleep(1)` em `main.py:134`, e a lógica de quebra/continue em `main.py:141-146` permanecem como estão.

### 4.2 `backend/app/get_video.py`
- **`_classify_error` (linhas 5-15)** — manter a função como está; é a fonte única de classificação.
- **`download_video_with_class` (linhas 37-75)** — refatorar conforme abaixo (sem alterar assinatura `(url, opts) -> tuple[bool, str]`):
  1. Construir `preflight_opts = {**ydl_opts, "ignoreerrors": False}` antes do `try` do dry-run.
  2. No bloco `try:` que envolve `extract_info(download=False)`, usar `preflight_opts` em vez de `ydl_opts`.
  3. Substituir `if not info: return (False, "other")` por uma classificação via `_classify_error` quando o pre-flight lançar exceção, e manter o retorno antecipado (sem iniciar o download real).
  4. Quando o pre-flight passar, chamar `_download(url, ydl_opts)` (com `ignoreerrors=True`).
  5. Remover o bloco `if bucket == "format_unavailable": ... fallback_opts = {**ydl_opts, 'format': 'best'} ...` (linhas 66-75), bem como o `print` `[fallback] 360p indisponível…` e `[fallback] Sucesso com formato 'best'…` associados.
  6. Preservar `ydl_opts.setdefault('format', 'best')` em `get_video.py:44` (default defensivo).
- **`_download` (linhas 18-34)** — manter como está; o `ignoreerrors=True` continua no `ydl_opts` recebido e o `except` segue chamando `_classify_error`.
- **Estrutura final proposta para `download_video_with_class`** (esboço conceitual, não editável neste plano):
  ```python
  def download_video_with_class(url, opts) -> tuple:
      ydl_opts = {'quiet': False, 'no_warnings': True, 'ignoreerrors': True, **opts}
      ydl_opts.setdefault('format', 'best')
      preflight_opts = {**ydl_opts, 'ignoreerrors': False}

      try:
          with yt_dlp.YoutubeDL(preflight_opts) as ydl:
              info = ydl.extract_info(url, download=False)
          if not info:
              return (False, "other")
      except yt_dlp.utils.DownloadError as e:
          bucket = _classify_error(e)
          return (False, bucket)
      except yt_dlp.utils.ExtractorError:
          return (False, "unsupported")
      except Exception:
          return (False, "other")

      return _download(url, ydl_opts)
  ```

## 5. Escopo excluído
- Qualquer arquivo fora de `backend/app/main.py` e `backend/app/get_video.py` (C4).
- Remoção ou renomeação de `__initi__.py`.
- Reescrita de `process_smart_batch`, `convert_to_netscape_format`, `_pick_embed_referer`.
- Mudança em `MAX_WORKERS`, `ThreadPoolExecutor`, diretório de download.
- Mudança no contrato HTTP `{message: string}` (C3).
- Suporte a novos provedores, DRM, proxy, throttling, retry exponencial.
- Mudanças em cookies, `Referer`, `User-Agent`, headers HTTP.
- Renomeação de buckets (`format_unavailable`, `embed_only`, `unsupported`, `other`, `ok`, `ok_fallback`) — C5.
- Remoção de `time.sleep(1)` em `main.py:134` e `time.sleep(2)` em `get_video.py:22, 33` — C6.
- Criação de testes automatizados (manter abordagem manual).

## 6. Riscos
- **R1** — Se o `preflight_opts` não sobrescrever corretamente `ignoreerrors`, a `DownloadError` continua suprimida e o sintoma original persiste. Mitigação: testar com a URL 1210147270 (CA2).
- **R2** — Se o `extract_info` retornar `info` válido porém com `formats` vazio (por outra razão), a função cairia no download real e poderia falhar de forma diferente. Mitigação: `ignoreerrors=True` no `_download` mantém a resiliência; o bucket `format_unavailable` ainda pode ser classificado lá.
- **R3** — O novo seletor pode mudar o resultado de vídeos que antes caiam no `best` (por não ter 360p) — porém o efeito é o desejado (mais opções), não regressão.
- **R4** — Remoção do fallback Python torna a função mais simples, mas se o seletor RF1 falhar em todos os encadeamentos (cenário improvável), o bucket `format_unavailable` do pre-flight já reflete a falha. Mitigação: CA2 confirma sucesso.
- **R5** — Regressão em vídeos YouTube/m3u8 se o seletor for menos permissivo (não é o caso — RF1 encadeia até `best`). Mitigação: CA5 (regressão manual).
- **R6** — Versão futura do yt-dlp pode alterar a string `"Requested format is not available"`, quebrando `_classify_error`. Mitigação: R6 já existia; não ampliada.
- **R7** — `setdefault('format', 'best')` em `get_video.py:44` pode parecer política duplicada, mas é default defensivo (sem override em `process_smart_batch`). Mitigação: comentário inline é fora de escopo; fica claro pela ausência de uso.

## 7. Mitigações
- **M1** — Usar `{**ydl_opts, "ignoreerrors": False}` (dict spread) em vez de mutação, garantindo que o `ydl_opts` original não seja alterado.
- **M2** — Manter a função centralizada `_classify_error` como single source of truth; nenhuma classificação é feita inline fora dela.
- **M3** — `process_smart_batch` em `main.py:136-146` já é o único ponto que imprime `⚠️ [bucket] Falha:` e `✅ [{bucket}] Download concluído:`. Como o pre-flight fica silencioso e `_download` não imprime, não há duplicação de log.
- **M4** — Smoke test YouTube e m3u8 antes de testar o caso alvo Vimeo (ordem recomendada).
- **M5** — Validar com a URL `tiexames.com.br/.../SESSAO=3281` após implementação (T1 da spec).

## 8. Critérios de aceite

| # | Critério | Verificável por |
|---|----------|-----------------|
| CA1 | `backend/app/main.py:116` contém exatamente o seletor encadeado de RF1, sem o seletor rígido antigo | inspeção direta do código |
| CA2 | O vídeo Vimeo `1210147270` (via URL tiexames ou via `player.vimeo.com`) é baixado com sucesso em pelo menos uma das tentativas | log mostra `✅ [...] Download concluído:` |
| CA3 | Nenhuma linha `⚠️ [other] Falha:` é emitida para a URL acima quando o seletor anterior falhava com o mesmo input | inspeção do log |
| CA4 | Em caso de falha real (vídeo indisponível, cookies inválidos), o bucket retornado é `format_unavailable`, `embed_only` ou `unsupported` — nunca `other` por causa de formato | inspeção do log |
| CA5 | Vídeos YouTube (`/watch`) e m3u8 diretos continuam baixando | regressão manual T4/T5 |
| CA6 | `/download_single` produz o mesmo resultado que `/download_smart_batch` para a mesma URL | regressão manual |
| CA7 | O log ainda distingue `formato indisponível`, `embed-only` e `outro` | inspeção direta |
| CA8 | Nenhum arquivo além de `backend/app/main.py` e `backend/app/get_video.py` foi modificado | `git status` / `git diff --name-only` |
| CA9 | O endpoint continua respondendo 200 OK com payload `{message: string}` | inspeção do response |
| CA10 | O bloco de fallback Python (`if bucket == "format_unavailable":` …) foi removido de `get_video.py` | inspeção direta / `git diff` |

## 9. Testes/checks necessários

| # | Teste | Resultado esperado |
|---|-------|---------------------|
| T1 | Manual com a URL `tiexames.com.br/.../SESSAO=3281` via extensão (CA1, CA2) | download concluído; log `✅ [ok] Download concluído:` |
| T2 | `POST /download_smart_batch` com `[tiexames_url, player_vimeo_url]` (CA2) | 200 OK + log de sucesso |
| T3 | `POST /download_smart_batch` com `[player_vimeo_url]` apenas (CA6) | 200 OK; `Referer=self`; download concluído |
| T4 | Regressão YouTube (vídeo `/watch`) | download concluído |
| T5 | Regressão m3u8 direto (URL `.m3u8`) | download concluído |
| T6 | `POST` com URL inválida (CA4, CA9) | 200 OK com `message`; log `⚠️ [unsupported\|embed_only\|other] Falha:`; mensagem final `❌ Nenhuma das URLs…` |
| T7 | Inspeção de `git diff --name-only` (CA8) | apenas `backend/app/main.py` e `backend/app/get_video.py` |
| T8 | Inspeção de `git diff backend/app/main.py` (CA1) | linha 116 com seletor de RF1 |
| T9 | Inspeção de `git diff backend/app/get_video.py` (CA10) | bloco `if bucket == "format_unavailable":` ausente |
| T10 | `cat downloads/` para confirmar artefato (T1, T2) | arquivo `.mp4` ou `.m4a` presente |
| T11 | `ls /tmp/tmp*.txt` após o job (cookies temp) | arquivo removido (comportamento atual preservado por `finally` em `main.py:151-153`) |

## 10. Ordem recomendada
1. **Pré-checagens** — confirmar versão do `yt-dlp` (`poetry run python -c "import yt_dlp; print(yt_dlp.version.__version__)"`) e revisar `pyproject.toml` para garantir que nada dependa de buckets renomeados.
2. **Edição de `backend/app/main.py:116`** — substituir o seletor (2.1).
3. **Edição de `backend/app/get_video.py`** — refatorar `download_video_with_class` (4.2): `preflight_opts`, retorno imediato no pre-flight, remoção do fallback Python.
4. **Smoke test YouTube (T4)** — regressão primária.
5. **Smoke test m3u8 (T5)** — regressão secundária.
6. **Teste alvo Vimeo (T1, T2, T3)** — confirmar CA1, CA2, CA3, CA4, CA6, CA9.
7. **Inspeção de diff (T7, T8, T9)** — confirmar CA8, CA10.
8. **Verificação de artefatos e cookies (T10, T11)** — confirmar side-effects.
9. **Se CA1 falhar** — revisar a string exata do seletor (C1).
10. **Se CA2 falhar** — verificar se `preflight_opts` está realmente com `ignoreerrors=False` (R1); rodar `yt-dlp --list-formats` na URL 1210147270 para confirmar as resoluções reais.
11. **Se CA3 ou CA4 falharem** — auditar a chamada de `_classify_error` no pre-flight e no `_download`; garantir que `info is None` não é classificado como `other` por motivo de formato.
12. **Se CA5 falhar** — investigar se o seletor de RF1 é compatível com YouTube/m3u8.
13. **Se CA8 falhar** — reverter diffs fora de `main.py`/`get_video.py`.
14. **Próxima skill** — `/tasks` (quebrar este plano em tarefas sequenciais) → `/implement` (executar com escopo mínimo) → `/validate` (rodar smoke tests e verificar CA1-CA10).

---

## Resumo da sessão

**Solicitação original**: o usuário invocou `/plan` com a especificação aprovada (após clarificação com decisões D1-D5) para criar um plano técnico de correção do fallback de formato Vimeo.

**Produto**: plano técnico com 10 seções detalhando objetivo, estratégia (7 itens, 2.1-2.7), arquivos impactados (`main.py:116` e `get_video.py`), alteração prevista por arquivo, escopo excluído, 7 riscos (R1-R7), 5 mitigações (M1-M5), 10 critérios de aceite (CA1-CA10), 11 testes manuais (T1-T11), e ordem de execução em 14 passos.

**Modo de operação**: plan — nenhum arquivo foi alterado.
