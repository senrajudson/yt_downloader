import yt_dlp

def get_id(url):
        try:

            ydl_options = {
            "listformats": True
            }

            with yt_dlp.YoutubeDL(ydl_options) as ydl:

                info = ydl.extract_info(url, download=False)
                info = ydl.sanitize_info(info)

                from pprint import pprint

                formats = info.get('formats', [])

                # pprint(formats)

                # favorite_formats = ['93-0', '93-1', '92-0', '92-1', '94-0', '94-1', '18', '233', "230"]
                id = ""
                formats_list = []

                for i in formats:
                        
                    format_id = i.get('format_id')
                    # pprint(format_id)
                    formats_list.append(format_id)
        except:
             formats_list = []

        return formats_list