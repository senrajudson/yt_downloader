import os
import re
import time
import random
import tempfile
from typing import List
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from concurrent.futures import ThreadPoolExecutor # <-- IMPORTANTE: Nova importação

from app.get_video import download_video

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

def process_smart_batch(videos: List[VideoItem], cookies: list):
    """
    Processa a lista de vídeos. O ThreadPoolExecutor vai rodar isso em paralelo.
    """
    netscape_cookies = convert_to_netscape_format(cookies)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
        tmp.write(netscape_cookies)
        cookie_path = tmp.name

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
                'format': 'best[height=360]/bestvideo[height=360]+bestaudio/best[height<=360]',
                'save_cookies': False 
            }

            print(f"🔄 Tentando baixar: {video.url}")

            time.sleep(1)
            
            sucesso = download_video(video.url, ydl_opts)
            
            if sucesso:
                print(f"✅ Download concluído com sucesso: {unique_title}")
                sucesso_geral = True
                break 
            else:
                print(f"⚠️ Falha ao baixar {video.url}. Tentando a próxima opção...")

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