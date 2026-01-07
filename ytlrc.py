#!/root/.bin/.venv/bin/python3

import yt_dlp
import requests
import os,sys

import re
from typing_tube import strip_ruby


INVISIBLE = {
    '\u200b',  # zero width space
    '\u200c',
    '\u200d',
    '\ufeff',  # BOM
}

def remove_invisible(s: str) -> str:
    return ''.join(ch for ch in s if ch not in INVISIBLE)


from utils import lyrics
from typing_tube import writetoml
pattern = re.compile(r"(\d+:\d+:\d+\.\d+)\s+-->\s+(\d+:\d+:\d+\.\d+)")

def parsetime(t:str)->float:
    h,m,s=t.split(":")
    return float(h)*3600+float(m)*60+float(s)

def parsevtt(text:str)->lyrics:
    lines=text.splitlines()
    i = 0
    end_time=""
    last=""
    while i < len(lines):
        match = pattern.search(lines[i])
        if match:
            start_time = match.group(1)
            if end_time== "" or  start_time == end_time:
                end_time=match.group(2)
            else:
                yield parsetime(end_time),""
                end_time=match.group(2)
            
            cur=[]
            while i + 1 < len(lines) and lines[i+1].strip()!="":
                cur.append(remove_invisible(lines[i+1].strip()))
                i += 1
            if len(cur)>1:
                print("warning: multiline detected")
            this=" ".join(cur)
            if this == last:
                continue
            last=this
            yield parsetime(start_time),this
            
        i += 1

def vtt_to_toml(text:str, toml_path:str,offset:float=None):
    return writetoml(parsevtt(text),toml_path,offset)

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

from collections.abc import Generator
def ytlrc(url)->tuple[str,Generator[tuple[str,str]]]:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if 'subtitles' not in info:
        raise Exception("no subtitles")
    
    def func():
        for lang in info['subtitles']:
            newlang=getlang(lang)
            if newlang==None:
                continue
            for format in info['subtitles'][lang]:
                fmt = format['ext']
                if fmt != "vtt":
                    continue
                for _ in range(10):
                    rsp=requests.get(format['url'],proxies=proxies)
                    if rsp.status_code==200:
                        break
                if rsp.status_code!=200:
                    raise Exception("not 200 code %d"%rsp.status_code)
                yield newlang,rsp.text
    it=func()
    return info["title"],it

from typing_tube import gettomlpath

langmap={
    "ja":"jp",
    "en":"en",
    "ko":"ko",
    "zh":"cn",
    "zh-cn":"cn",
    "zh-hans":"cn",
    "zh-tw":"tw",
    "zh-hant":"tw",
    "zh-hk":"tw"
}

def getlang(code:str)->str:
    code=code.lower()
    if code in langmap:
        return langmap[code]
    for k,v in langmap.items():
        if code.startswith(k):
            print("warning: matching %s as %s"%(code,k))
            return v
    print("cannot find lang:%s, skipping"%code)
    return None



if __name__=="__main__":
    title,lyrics=ytlrc(sys.argv[1])
    offset=None
    if len(sys.argv)>2:
        title=sys.argv[2]
    if len(sys.argv)>3:
        offset=float(sys.argv[3])
    for lang,vtt in lyrics:
        toml=gettomlpath(title,lang)
        vtt_to_toml(vtt, toml,offset=offset)
        print("write file",toml)