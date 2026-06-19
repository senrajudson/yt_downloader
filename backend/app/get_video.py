import time
import yt_dlp

def download_video(url, opts):
    # Nota: Removi o get_id() aqui porque ele não estava sendo retornado ou
    # usado de forma que afetasse o download diretamente, e poderia causar mais erros.

    ydl_opts = {
        # 'external_downloader': 'ffmpeg', # para baixar livestreams, não necessário
        # 'hls_use_mpegts': True, # para baixar livestreams, não necessário
        'quiet': False,
        'no_warnings': True, # Mudado para True para limpar o log
        'ignoreerrors': True, # Essencial para o modo Batch
        **opts # Recebe cookiefile e outtmpl da main
    }

    try:
        # Forçamos o fallback de formato caso a opção da main falhe
        ydl_opts.setdefault('format', 'best')
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Fazemos um dry-run primeiro
            info = ydl.extract_info(url, download=False)
            
            if info:
                # Se passou do dry-run, podemos baixar
                ydl.download([url])
                time.sleep(2)
                return True
            else:
                return False
                
    except yt_dlp.utils.DownloadError as e:
        # Pega erros comuns de download (Ex: Unsupported URL)
        print(f"\n[Filtro] Ignorando URL não suportada: {url}")
        return False
        
    except yt_dlp.utils.ExtractorError as e:
        # Pega erros de extração/login
        print(f"\n[Filtro] Falha ao extrair dados de: {url}")
        return False

    except Exception as e:
        # Pega qualquer outra coisa (evita quebrar a API)
        print(f"\n[Erro Geral] Ignorado ao processar {url}: {e}")
        time.sleep(2)
        return False

# ==================================
# Se for rodar o arquivo diretamente
# ==================================
if __name__ == '__main__':
    URL = "https://www.youtube.com/live/-uBf1O52byc"
    opts = {'format': 'bestvideo+bestaudio/best', 'outtmpl': '%(title)s.%(ext)s'}
    download_video(URL, opts)