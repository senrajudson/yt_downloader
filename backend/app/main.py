import os
import re
import time
import tempfile
from typing import List
from pathlib import Path
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.get_video import download_video

app = FastAPI()

# Configuração de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

home_dir = str(Path.home())
download_path = os.path.join(home_dir, 'projetos/yt_downloader/downloads')
os.makedirs(download_path, exist_ok=True)

def convert_to_netscape_format(cookies_list):
    """Converte a lista de cookies do Chrome para o formato Netscape."""
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
# FUNÇÕES DE BACKGROUND
# ==========================================

def process_smart_batch(videos: List[VideoItem], cookies: list):
    """
    Processa a lista de vídeos de forma inteligente.
    Tenta baixar um por um; se tiver sucesso, para o loop (evitando duplicatas).
    """
    # 1. Prepara o arquivo de cookies UMA única vez para o lote inteiro
    netscape_cookies = convert_to_netscape_format(cookies)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
        tmp.write(netscape_cookies)
        cookie_path = tmp.name

    try:
        sucesso_geral = False
        
        # 2. Loop inteligente (Fallback)
        for video in videos:
            if video.url.lower().endswith('.gif'):
                print(f"⏩ Pulando {video.url} por ser um arquivo GIF.")
                continue 

            # Limpa o título (usa o título vindo da extensão)
            safe_title = re.sub(r'[\\/*?:"<>|]', "", video.title).strip()
            safe_title = safe_title.replace(" ", "_")

            # 2. Gera um timestamp único (Tempo atual + número aleatório para garantir)
            timestamp = f"{int(time.time())}"
            unique_title = f"{safe_title}_{timestamp}"

            # Configurações do yt-dlp
            ydl_opts = {
                'cookiefile': cookie_path,
                # Usamos o NOSSO safe_title em vez de %(title)s
                'outtmpl': f'{download_path}/{unique_title}.%(ext)s',
                'format': 'best[height=360]/bestvideo[height=360]+bestaudio/best[height<=360]',
                'save_cookies': False 
            }

            print(f"🔄 Tentando baixar: {video.url}")
            
            # Chama a função do seu get_video.py
            sucesso = download_video(video.url, ydl_opts)
            
            if sucesso:
                print(f"✅ Download concluído com sucesso: {safe_title}")
                sucesso_geral = True
                # Break é CRUCIAL! Se a URL da página funcionou, não precisamos baixar o .m3u8 da rede.
                break 
            else:
                print(f"⚠️ Falha ao baixar {video.url}. Tentando a próxima opção da lista...")

        if not sucesso_geral:
            print("❌ Nenhuma das URLs enviadas pela extensão pôde ser baixada.")

    finally:
        # 3. Limpeza final
        if os.path.exists(cookie_path):
            os.remove(cookie_path)


# ==========================================
# ENDPOINTS
# ==========================================

@app.post("/download_single")
async def single_download(req: SingleDownloadRequest, background_tasks: BackgroundTasks):
    # Transforma o SingleRequest em uma lista de 1 item e manda pro mesmo processador inteligente
    video_item = VideoItem(url=req.url, title=req.title)
    background_tasks.add_task(process_smart_batch, [video_item], req.cookies)
    return {"message": f"Iniciando download de: {req.title}"}

@app.post("/download_smart_batch")
async def smart_batch_download(req: SmartBatchRequest, background_tasks: BackgroundTasks):
    # Enviamos a LISTA INTEIRA para UMA única tarefa de background
    background_tasks.add_task(process_smart_batch, req.videos, req.cookies)
    return {"message": f"Processando lista inteligente com {len(req.videos)} links/camadas!"}