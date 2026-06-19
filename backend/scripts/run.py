import subprocess
import pandas as pd

cmd_download = ['python', '-m', 'src.get_video', '--remote-components', 'ejs:github', '--format', '93-1']

# def pipe_cmd():

#     cmd_list = ['python', '-m', 'src.get_video', '--list-formats']

#     result = subprocess.run(cmd_list, capture_output=True, text=True)

#     # df = pd.Series(result, index=None)

#     # df = pd.DataFrame(df)

#     return result

# print(pipe_cmd())

cmd_list = ['python', '-m', 'src.get_video', '--list-formats']

# result = subprocess.run(cmd_list, capture_output=False, text=True)

ydl_options = {
    "listformats": True
}

import yt_dlp

URL = "https://www.youtube.com/live/-uBf1O52byc"

def get_id(URL):

    with yt_dlp.YoutubeDL(ydl_options) as ydl:

        info = ydl.extract_info(URL, download=False)
        info = ydl.sanitize_info(info)

        formats = info.get('formats', [])

        from pprint import pprint

        # pprint(formats)

        favorite_formats = ['93-0', '93-1', '92-0', '92-1', '94-0', '94-1', '18']
        id = ""

        for i in formats:
            for j in favorite_formats:
                if j == i.get('format_id'):
                    id = j
                    break

    return id