import os
import re
import time
import random
import tempfile
from typing import List, Optional
from pathlib import Path
from urllib.parse import urlparse
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel  
from concurrent.futures import ThreadPoolExecutor # <-- IMPORTANTE: Nova importação

from app.get_video import download_video_with_class

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

home_dir = str(Path.home())
download_path = os.path.join(home_dir, 'projetos/yt_downloader/downloads')
os.makedirs(download_path, exist_ok=True)

# ==========================================
# CONFIGURAÇÃO DE MULTITHREADING E FILA
# ==========================================
# Variável global para definir o número máximo de downloads simultâneos
MAX_WORKERS = 4 

# O Executor cria as threads e gerencia a fila (queue) automaticamente
download_queue = ThreadPoolExecutor(max_workers=MAX_WORKERS)


def convert_to_netscape_format(cookies_list):
    # ... (Mantenha o seu código de conversão de cookies intacto aqui) ...
    lines = ["# Netscape HTTP Cookie File", "# https://curl.haxx.se/rfc/cookie_spec.html", "# This is a generated file!  Do not edit.", ""]
    for cookie in cookies_list:
        domain = cookie.get('domain', '')
        include_subdomains = 'TRUE' if domain.startswith('.') else 'FALSE'
        path = cookie.get('path', '/')
        secure = 'TRUE' if cookie.get('secure') else 'FALSE'
        expires = int(cookie.get('expirationDate', 0))
        name = cookie.get('name', '')
        value = cookie.get('value', '')
        line = f"{domain}\t{include_subdomains}\t{path}\t{secure}\t{expires}\t{name}\t{value}"
        lines.append(line)
    return "\n".join(lines)

# ==========================================
# MODELOS PYDANTIC
# ==========================================

class SingleDownloadRequest(BaseModel):
    url: str
    title: str
    cookies: list

class VideoItem(BaseModel):
    url: str
    title: str

class SmartBatchRequest(BaseModel):
    videos: List[VideoItem]
    cookies: list

# ==========================================
# FUNÇÕES WORKER (O que roda em paralelo)
# ==========================================

def _pick_embed_referer(videos: List[VideoItem]) -> Optional[str]:
    for video in videos:
        parsed = urlparse(video.url)
        hostname = parsed.hostname or ""
        path = parsed.path or ""
        if "vimeo.com" in hostname:
            continue
        if path.endswith(".m3u8") or path.endswith(".mp4"):
            continue
        return video.url
    return None


def process_smart_batch(videos: List[VideoItem], cookies: list):
    """
    Processa a lista de vídeos. O ThreadPoolExecutor vai rodar isso em paralelo.
    """
    netscape_cookies = convert_to_netscape_format(cookies)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
        tmp.write(netscape_cookies)
        cookie_path = tmp.name

    embed_referer = _pick_embed_referer(videos)

    try:
        sucesso_geral = False
        
        for video in videos:
            if video.url.lower().endswith('.gif'):
                print(f"⏩ Pulando {video.url} por ser um arquivo GIF.")
                continue 

            safe_title = re.sub(r'[\\/*?:"<>|]', "", video.title).strip()
            safe_title = safe_title.replace(" ", "_")

            timestamp = f"{int(time.time())}_{random.randint(1000, 9999)}"
            unique_title = f"{safe_title}_{timestamp}"

            ydl_opts = {
                'cookiefile': cookie_path,
                'outtmpl': f'{download_path}/{unique_title}.%(ext)s',
                'format': (
                    "bestvideo*[height<=360]+bestaudio/"
                    "best[height<=360]/"
                    "bestvideo*+bestaudio/"
                    "best"
                ),
                'save_cookies': False 
            }

            if "player.vimeo.com" in video.url:
                headers = {}
                headers['Referer'] = embed_referer or video.url
                headers['User-Agent'] = (
                    'Mozilla/5.0 (X11; Linux x86_64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/120.0.0.0 Safari/537.36'
                )
                ydl_opts['http_headers'] = headers
                ref_str = embed_referer or "self"
                print(f"🔄 Tentando: {video.url} [Referer: {ref_str}]")
            else:
                print(f"🔄 Tentando: {video.url}")

            time.sleep(1)

            ok, bucket = download_video_with_class(video.url, ydl_opts)

            if ok:
                print(f"✅ [{bucket}] Download concluído: {unique_title}")
                sucesso_geral = True
                break
            else:
                print(f"⚠️ [{bucket}] Falha: {video.url}")
                if bucket == "embed_only":
                    print("⏩ embed_only não retentável; próxima URL...")
                    continue

        if not sucesso_geral:
            print("❌ Nenhuma das URLs enviadas pôde ser baixada.")

    finally:
        if os.path.exists(cookie_path):
            os.remove(cookie_path)


# ==========================================
# ENDPOINTS (Rotas da API)
# ==========================================

@app.post("/download_single")
async def single_download(req: SingleDownloadRequest):
    video_item = VideoItem(url=req.url, title=req.title)
    
    # Substituímos o background_tasks pelo nosso executor com limite!
    download_queue.submit(process_smart_batch, [video_item], req.cookies)
    
    return {"message": f"Iniciando download (ou na fila): {req.title}"}

@app.post("/download_smart_batch")
async def smart_batch_download(req: SmartBatchRequest):
    
    # Substituímos o background_tasks pelo nosso executor com limite!
    download_queue.submit(process_smart_batch, req.videos, req.cookies)
    
    return {"message": f"Adicionado à fila de downloads. Máximo de {MAX_WORKERS} simultâneos!"}