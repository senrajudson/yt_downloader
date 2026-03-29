import os
import re
import json
import time
import random
import tempfile
from typing import List
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.get_video import download_video

app = FastAPI()

# Configuração de CORS para permitir que a extensão fale com a API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Em produção, use o ID da sua extensão aqui
    allow_methods=["*"],
    allow_headers=["*"],
)

def convert_to_netscape_format(cookies_list):
    """
    Converte a lista de cookies do Chrome para o formato Netscape que o yt-dlp exige.
    """
    lines = ["# Netscape HTTP Cookie File", "# https://curl.haxx.se/rfc/cookie_spec.html", "# This is a generated file!  Do not edit.", ""]
    
    for cookie in cookies_list:
        # A API do Chrome envia dicts.
        domain = cookie.get('domain', '')
        
        # O campo 'include_subdomains' no formato Netscape é 'TRUE' se o domínio começar com ponto
        include_subdomains = 'TRUE' if domain.startswith('.') else 'FALSE'
        
        path = cookie.get('path', '/')
        secure = 'TRUE' if cookie.get('secure') else 'FALSE'
        
        # O Chrome manda expirationDate em float. O yt-dlp precisa em inteiro (Unix timestamp).
        expires = int(cookie.get('expirationDate', 0))
        
        name = cookie.get('name', '')
        value = cookie.get('value', '')
        
        line = f"{domain}\t{include_subdomains}\t{path}\t{secure}\t{expires}\t{name}\t{value}"
        lines.append(line)
        
    return "\n".join(lines)


# ==========================================
# MODELOS PYDANTIC (Estruturas de Dados)
# ==========================================

class SingleDownloadRequest(BaseModel):
    url: str
    title: str
    cookies: list

# Novos modelos para o Batch Inteligente
class VideoItem(BaseModel):
    url: str
    title: str

class SmartBatchRequest(BaseModel):
    videos: List[VideoItem]
    cookies: list


# ==========================================
# FUNÇÕES DE BACKGROUND
# ==========================================

def run_yt_dlp_custom_title(url: str, custom_title: str, cookies: list):
    netscape_cookies = convert_to_netscape_format(cookies)
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
        tmp.write(netscape_cookies)
        cookie_path = tmp.name

    try:
        # Limpa o título para evitar erros no Linux/Windows (remove caracteres inválidos para pastas)
        safe_title = re.sub(r'[\\/*?:"<>|]', "", custom_title).strip()
        safe_title = safe_title.replace(" ", "_") # Troca espaços por underline
        
        unique_id = f"{int(time.time())}_{random.randint(1000, 9999)}"
        
        ydl_opts = {
            'cookiefile': cookie_path,
            # Forçamos o título que veio da extensão em vez de deixar o yt-dlp adivinhar
            'outtmpl': f'/home/judson/projetos/yt_downloader/downloads/{safe_title}_{unique_id}.%(ext)s', 
            'save_cookies': False 
        }
        
        os.makedirs('/home/judson/projetos/yt_downloader/downloads/', exist_ok=True)
        download_video(url, ydl_opts)
        
    finally:
        if os.path.exists(cookie_path):
            os.remove(cookie_path)


# ==========================================
# ENDPOINTS (Rotas da API)
# ==========================================

@app.post("/download_single")
async def single_download(req: SingleDownloadRequest, background_tasks: BackgroundTasks):
    # Agendamos a tarefa passando a URL, o Título e os Cookies
    background_tasks.add_task(run_yt_dlp_custom_title, req.url, req.title, req.cookies)
    return {"message": f"Iniciando download de: {req.title}"}

@app.post("/download_smart_batch")
async def smart_batch_download(req: SmartBatchRequest, background_tasks: BackgroundTasks):
    # Itera sobre cada vídeo encontrado e agenda o download individualmente
    for video in req.videos:
        background_tasks.add_task(run_yt_dlp_custom_title, video.url, video.title, req.cookies)
        
    return {"message": f"Processando {len(req.videos)} vídeos!"}