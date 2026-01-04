#!/root/.bin/.venv/bin/python3

import yt_dlp
import requests
import os,sys
import html


import re
from typing_tube import strip_ruby

pattern = re.compile(r"(\d+:\d+:\d+\.\d+)\s+-->\s+(\d+:\d+:\d+\.\d+)")
def vtt_to_toml(text:str, toml_path:str,offset:float=0):
    lines=text.splitlines()
    entries = {}
    i = 0
    end_time=""
    while i < len(lines):
        match = pattern.search(lines[i])
        if match:
            start_time = match.group(1)
            if end_time== "" or  start_time == end_time:
                end_time=match.group(2)
            else:
                entries[end_time]=""
                end_time=match.group(2)
            # 下一行即为字幕文本
            if i + 1 < len(lines) and lines[i+1].strip():
                text = lines[i+1].strip()
                entries[start_time]=text
                i += 1

        i += 1

    with open(toml_path, 'w', encoding='utf-8') as f:
        f.write("lyrics = [\n")
        lasttext=None
        for t, text in entries.items():
            if offset!=0:
                t=stroffset(t,offset)
            text=strip_ruby(text)
            if text==lasttext:
                continue
            else:
                lasttext=text
            f.write(f'    {{time = {t}, text = "{text.replace('"',r'\"')}"}},\n')
        f.write("]\n")

from typing_tube import format_time

def stroffset(t:str,offset:float)->str:
    parts=t.split(":")
    offset+=float(parts[2])
    offset+=float(parts[1])*60
    offset+=float(parts[0])*3600
    return format_time(offset*100000)


proxy = "http://proxy.lan:1080"

proxies= {
     "https":proxy
}

ydl_opts = {
    "proxy": proxy
}


def ytlrc(url)->tuple[str,dict[str,str]]:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if 'subtitles' not in info:
        raise Exception("no subtitles")
    m={}
    for lang in info['subtitles']:
        for format in info['subtitles'][lang]:
                fmt = format['ext']
                if fmt == "vtt":
                    rsp=requests.get(format['url'],proxies=proxies)
                    m[lang]=rsp.text
    return info['title'],m

from typing_tube import gettomlpath

langmap={
    "ja":"jp",
    "en":"en",
    "ko":"ko",
    "zh":"cn",
}

def getlang(code:str)->str:
    code=code.lower()
    if code in langmap:
        return langmap[code]
    for k,v in langmap.items():
        if code.startswith(k):
            return v
    print("cannot find lang:%s, skipping"%code)
    return None



if __name__=="__main__":
    title,lyrics=ytlrc(sys.argv[1])
    offset=0
    if len(sys.argv)>2:
        title=sys.argv[2]
    if len(sys.argv)>3:
        offset=float(sys.argv[3])
    for lang,vtt in lyrics.items():
        lang=getlang(lang)
        if lang==None:
            continue
        toml=gettomlpath(title,lang)
        vtt_to_toml(vtt, toml,offset=offset)
        print("write file",toml)