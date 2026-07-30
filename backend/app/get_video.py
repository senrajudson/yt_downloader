import time
import yt_dlp


def _classify_error(e: Exception) -> str:
    msg = str(e)
    if isinstance(e, yt_dlp.utils.DownloadError):
        if "Requested format is not available" in msg:
            return "format_unavailable"
        if "embed-only" in msg or "embedding URL" in msg:
            return "embed_only"
        return "unsupported"
    if isinstance(e, yt_dlp.utils.ExtractorError):
        return "unsupported"
    return "other"


def _download(url, ydl_opts) -> tuple:
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        time.sleep(2)
        return (True, "ok")
    except yt_dlp.utils.DownloadError as e:
        bucket = _classify_error(e)
        print(f"\n[{bucket}] Falha ao baixar: {url}")
        return (False, bucket)
    except yt_dlp.utils.ExtractorError:
        print(f"\n[unsupported] Falha ao extrair: {url}")
        return (False, "unsupported")
    except Exception as e:
        print(f"\n[other] Erro ao processar {url}: {e}")
        time.sleep(2)
        return (False, "other")


def download_video_with_class(url, opts) -> tuple:
    ydl_opts = {
        'quiet': False,
        'no_warnings': True,
        'ignoreerrors': True,
        **opts
    }
    ydl_opts.setdefault('format', 'best')

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                return (False, "other")
    except yt_dlp.utils.DownloadError as e:
        bucket = _classify_error(e)
        print(f"\n[{bucket}] Falha no dry-run: {url}")
        return (False, bucket)
    except yt_dlp.utils.ExtractorError:
        print(f"\n[unsupported] Falha ao extrair (dry-run): {url}")
        return (False, "unsupported")
    except Exception as e:
        print(f"\n[other] Erro no dry-run {url}: {e}")
        return (False, "other")

    ok, bucket = _download(url, ydl_opts)
    if ok:
        return (True, bucket)

    if bucket == "format_unavailable":
        print(f"\n[fallback] 360p indisponível para {url}; tentando 'best'")
        fallback_opts = {**ydl_opts, 'format': 'best'}
        ok, bucket = _download(url, fallback_opts)
        if ok:
            print(f"\n[fallback] Sucesso com formato 'best': {url}")
            return (True, "ok_fallback")
        print(f"\n[fallback] Falha com 'best' para {url} [{bucket}]")

    return (False, bucket)


def download_video(url, opts):
    ok, _ = download_video_with_class(url, opts)
    return ok


if __name__ == '__main__':
    URL = "https://tiexames.com.br/novoensino/vimeo/player.php?SESSAO=3281"
    opts = {'format': 'bestvideo+bestaudio/best', 'outtmpl': '%(title)s.%(ext)s'}
    download_video(URL, opts)