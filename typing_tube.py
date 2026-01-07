from extract_timing import format_time
from search_song import search_song
import os,sys
import requests

def parse_file(text:str)->tuple[str,dict[float,str]]:
    m={}
    lines=text.splitlines()
    head=lines[0]
    lines=lines[1:]
    for line in lines:
        line=line.strip()
        parts=line.split("\t")
        if len(parts)==1:
            tstr=parts[0]
            line=""
        elif parts[1]=="end":
            continue
        else:
            tstr=parts[0]
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
        num=int(title)
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

def getlrc(num:str)->str:
    rsp=requests.post("https://typing-tube.net/movie/lyrics/"+num,headers={
        "Origin": "https://typing-tube.net",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101 Firefox/144.0",
        "Referer": "https://typing-tube.net/movie/show/"+num
    })
    return rsp.text

from urllib.parse import quote
urlregex=re.compile(r'<a href="/movie/show/[0-9]{5}">.*?</a>')
def net_search_song(name:str)->dict[str,str]:
    url="https://typing-tube.net/?q="+quote(name)
    m=dict()
    for page in range(1,100):
        rsp=requests.get(url+"&page=%d"%page)
        for href in urlregex.findall(rsp.text):
            m[href[21:27]]=href[28:-4]
        if r'→</a>' not in rsp.text:
            break
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

from utils import conv_pv_num,find_offset,lyrics

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
        for k,v in lrc:
            k=k+offset
            if k<0:
                continue
            f.write(f'    {{time = {format_time(k*100000)}, text = "{strip_ruby(v).replace('"',r'\"')}"}},\n')
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
    _,lrc=parse_file(getlrc(tt_id))
    toml_path=os.path.join(lyrics_outdir,"%d_jp.toml"%input_num)
    offset=float(0)
    if len(sys.argv)>3 and sys.argv[3][0] in ('+','-'):
        offset=float(sys.argv[3])
    writetoml(lrc,toml_path,offset=offset)
    

