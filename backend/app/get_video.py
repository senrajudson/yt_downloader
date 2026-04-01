import time
import yt_dlp
from app.utils import get_id

def download_video(url, opts):
    # Mesclamos as opções padrão com as que vieram da API (que contêm os cookies)

    video_format, formats_list, favorites = get_id(url)

    ydl_opts = {
        # 'external_downloader': 'ffmpeg', # para baixar livestreams, não necessário
        # 'hls_use_mpegts': True, # para baixar livestreams, não necessário
        'quiet': False,
        'no_warnings': False,
        'format':video_format,
        **opts # Aqui entram o 'cookiefile' e o 'outtmpl' enviados pela main
    }

    try:

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        time.sleep(2)
    
    except: 
        print('Formato não listado, movendo para o próximo vídeo',
              "\nMy list: ", favorites,
              "\nList: ", formats_list
              )
        
        time.sleep(2)

if __name__ == '__main__':
    
    URL = "https://www.youtube.com/watch?v=zFjd2q2qrn4"

    download_video(URL)
