from search_song import search_song
import os,sys
import requests
from html.parser import HTMLParser

def parse_file(text:str)->tuple[str,dict[float,str]]:
    m={}
    lines=text.splitlines()
    head=lines[0]
    lines=lines[1:]
    for line in lines:
        line=line.strip()
        parts=line.split("\t")
        tstr=parts[0]
        if len(parts)==1:
            line=""
        elif parts[1]=="end":
            line=""
        else:
            line=parts[1]
        m[float(tstr)]=line
    return head,m

import re
import html

rt_regex=re.compile(r'<rt>.*?</rt>')
rp_regex=re.compile(r'</?rp[^>]*>')
ruby_regex=re.compile(r'</?ruby[^>]*>')
space_regex=re.compile(r'\s+')
html_regex = re.compile(r'<.*?>')

def strip_ruby(text: str) -> str:
    # 1) 先去掉所有的 <rt>...</rt> 内容
    text = rt_regex.sub('', text)

    # 2) 去掉 <rp> 标记（如果有，通常是括号用来兼容旧浏览器）
    text = rp_regex.sub('', text)

    # 3) 去掉 <ruby> 和 </ruby> 标签本身（保留中间的基文字）
    text = ruby_regex.sub('', text)

    # cleanup all other html tags
    text= html_regex.sub('',text)

    # 4) 清理多余空格（可选：把多个空白合为一个，并修整首尾）
    text = space_regex.sub(' ', text).strip()

    return html.unescape(text)


from config import lyrics_outdir
from utils import ask_for_num,ask_yes_no,conv_pv_num

def gettomlpath(title:str,lang="jp")->str:
    toml_path=None
    try:
        if type(title)==str:
            num=int(title)
        elif type(title)==int:
            num=title
        else:
            raise TypeError()
        toml_path=os.path.join(lyrics_outdir,"%d_%s.toml"%(num,lang))
    except:
        for part in title.split():
            for dir,pvid,name in search_song(part):
                print("matched",dir,pvid,name)
                toml_path=os.path.join(lyrics_outdir,"%s_%s.toml"%(pvid.split("_")[1],lang))
                break
            if toml_path!=None:
                break
    if toml_path==None:
        print("not found")
        sys.exit(1)
    return toml_path

from fetch_lyrics import fetch_page,fetch_lyrics_raw,decrypt_lyrics

def getlrc(num:str)->str:
    lrc,_=getlrc_ex(num)
    return lrc

def getlrc_ex(num:str)->tuple[str,str]:
    game_token, lyrics_key, csrf_token, cookies, _yt_id = fetch_page(num)
    data = fetch_lyrics_raw(num, game_token, csrf_token, cookies)
    encrypted = data["encrypted"]
    iv = data["iv"]
    auth_tag = data["auth_tag"]
    lyrics = decrypt_lyrics(lyrics_key, encrypted, iv, auth_tag)
    return lyrics,_yt_id

from urllib.parse import quote


def _attrs_dict(attrs):
    return {k: v for k, v in attrs}


class _MovieCardParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.cards: list[tuple[str, str]] = []  # (movie_num, title)
        self._in_title = False
        self._current_num: str | None = None
        self._title_buf: list[str] = []
        self._title_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag == "a" and any(k == "href" and v.startswith("/movie/show/") for k, v in attrs):
            self._current_num = _attrs_dict(attrs)["href"][len("/movie/show/"):]
            self._title_buf = []
            self._in_title = False
            self._title_depth = 0
        if self._current_num and tag == "span" and any(k == "class" and v == "movie-title-text" for k, v in attrs):
            self._in_title = True
            self._title_buf = []
            self._title_depth = 1

    def handle_endtag(self, tag):
        if self._in_title and tag == "span":
            self._title_depth -= 1
            if self._title_depth == 0:
                self._in_title = False
                title = "".join(self._title_buf).strip()
                if self._current_num and title:
                    self.cards.append((self._current_num, title))

    def handle_data(self, data):
        if self._in_title:
            self._title_buf.append(data)


def _has_more_pages(html_text: str) -> bool:
    return "Page " in html_text and "disabled" not in html_text.split("disabled", 1)[1] if "disabled" in html_text else True


def net_search_song(name: str) -> dict[str, str]:
    url = "https://typing-tube.net/?q=" + quote(name)
    m: dict[str, str] = {}
    page = 1
    while page <= 100:
        rsp = requests.get(url + "&page=%d" % page)
        parser = _MovieCardParser()
        parser.feed(rsp.text)
        for num, title in parser.cards:
            m[num] = title
        if not _has_more_pages(rsp.text):
            break
        page += 1
    return m

from mml import diva_db_file
from config import mod_dir
def get_title(pvnum:int)->str:
    for dir in os.listdir(mod_dir):
        full=os.path.join(mod_dir,dir,r'rom\mod_pv_db.txt')
        if os.path.exists(full):
            db:dict[str,str]=diva_db_file(full)
            db.readlines()
            name=db.get("pv_%03d.song_name"%pvnum,None)
            if name:
                return name

from utils import conv_pv_num,find_offset,lyrics,format_float




def writetoml(lrc:lyrics,toml_path:str,offset:float=None):
    if offset==None:
        try:
            num=int(os.path.basename(toml_path).split("_")[0])
            offset=find_offset(num)
            if offset!=0:
                print("writing with auto found offset %f"%offset)
        except:
            print("cannot find auto offset")
            offset=0
    elif type(offset)==float:
        pass
    else:
        offset=0

    if type(lrc)==dict:
        lrc=lrc.items()
    if os.path.exists(toml_path):
        if not ask_yes_no("%s exists, overwrite?"%toml_path):
            return
    with open(toml_path, 'w', encoding='utf-8') as f:
        f.write("lyrics = [\n")
        last=""
        for k,v in lrc:
            if v==last:
                continue
            else:
                last=v
            k=k+offset
            if k<0:
                continue
            f.write(f'    {{time = {format_float(k)}, text = "{strip_ruby(v).replace('"',r'\"')}"}},\n')
        f.write("]\n")
    print('write to file "%s"'%toml_path)

from search_song import search_song

if __name__=="__main__":
    try:
        input_num=conv_pv_num(sys.argv[1])
    except:
        title=sys.argv[1]
        if len(sys.argv)>2:
            input_num=int(sys.argv[2])
        else:
            _,input_num,_=next(search_song(title))
            input_num=conv_pv_num(input_num)
    else:
        title=get_title(input_num)
    if not title:
        print("cannot find pv_%03d"%input_num)
        sys.exit(1)
    songlist=net_search_song(title)
    if len(songlist)==0:
        print("cannot find %s in typing-tube"%title)
        sys.exit(1)
    elif len(songlist)>1:
        mapdict={}
        index=1
        for num,ti in songlist.items():
            print("%d\t%s"%(index,ti))
            mapdict[index]=num
            index+=1
        tt_id:str=mapdict[ask_for_num("please select a title")]
    else:
        tt_id=next(iter(songlist))
    lrcstr,yt_id=getlrc_ex(tt_id)
    _,lrc=parse_file(lrcstr)
    toml_path=gettomlpath(input_num)
    offset=float(0)
    if len(sys.argv)>3 and sys.argv[3][0] in ('+','-'):
        offset=float(sys.argv[3])
    writetoml(lrc,toml_path,offset=offset)

    usm_path=os.path.dirname(lyrics_outdir) + f"/rom/movie/pv_{input_num}.usm"
    if not os.path.exists(usm_path):
        from yt_dlp_to_usm import yt_dlp_to_usm
        yt_dlp_to_usm("https://youtu.be/"+yt_id,output=usm_path)


    

