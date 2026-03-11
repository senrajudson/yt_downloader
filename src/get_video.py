import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yt_dlp
import yt_dlp.options

create_parser = yt_dlp.options.create_parser

def parse_options(opts):
    patched_parser = create_parser()
    patched_parser.defaults.update({
        'ignoreerrors': False,
        # 'retries': 0,
        'fragment_retries': 0,
        'extract_flat': False,
        'concat_playlist': 'never',
        'update_self': False,
    })

    yt_dlp.options.create_parser = lambda: patched_parser

    try:
        return yt_dlp.parse_options(opts)
    
    finally:
        yt_dlp.options.create_parser = create_parser

default_opts = parse_options([]).ydl_opts

def cli_to_api(opts, cli_defaults=False):
    opts = (yt_dlp.parse_options if cli_defaults else parse_options)(opts).ydl_opts

    diff = {k: v for k, v in opts.items() if default_opts[k] != v}
    if 'postprocessors' in diff:
        diff['postprocessors'] = [pp for pp in diff['postprocessors'] if pp not in default_opts['postprocessors']]

    return diff

if __name__ == '__main__':

    from pprint import pprint

    print('\nThe arguments passed translate to:\n')
    pprint(cli_to_api(sys.argv[1:]))
    print('\nCombining these with the CLI defaults gives:\n')
    pprint(cli_to_api(sys.argv[1:], True))

    
    URL = "https://www.youtube.com/watch?v=C_YcIrq_P_4&t=215s"

    with yt_dlp.YoutubeDL(cli_to_api(sys.argv[1:], True)) as ydl:

        info = ydl.extract_info(URL, download=False)
        info = ydl.sanitize_info(info)

        # print(info)

    # ydl = yt_dlp.YoutubeDL(cli_to_api(sys.argv[1:], True))

    # ydl.download(URL)



# ydl_opts = {
#     'format-sort': 'res:480',
# }

# ydl = yt_dlp.YoutubeDL(ydl_opts)
# ydl.download(URL)

# info = ""

# with yt_dlp.YoutubeDL(ydl_opts) as ydl:

#     ydl.download()

#     info = ydl.extract_info(URL)
#     info = ydl.sanitize_info(info)

# youtube-dl -F "ttps://www.youtube.com/watch?v=C_YcIrq_P_4&t=215s"

