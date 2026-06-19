# Download Videos

Downloader de vídeos usando yt-dlp.

## Pré-requisitos

- Python 3.11+
- ffmpeg instalado (`sudo apt install ffmpeg` no Ubuntu/Debian)

## Instalação

```bash
cd yt_downloader
poetry install
```

## Uso

```bash
cd backend/app
poetry run python get_video.py
```

O vídeo será baixado na pasta atual.

## Mudar o vídeo

Edite a variável `URL` no arquivo `backend/app/get_video.py` (linha 53) e execute novamente.
