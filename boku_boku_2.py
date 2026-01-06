



from lrc2toml import read_lrc
from utils import lyrics,lyricsOffsetX
from typing_tube import format_time
import sys
from typing_tube import gettomlpath
from utils import ask_yes_no
import os


MAX_CHAR = 50
CHAR_SPLIT = 9
CHAR_SIZE = 36
MAX_ALPHA = 0xC0
ALPHA_STEP = MAX_ALPHA//MAX_CHAR


def genlongline(last:float,start:float,end:float,long:str)->lyricsOffsetX:
    l=len(long)
    step=(end-start)/l

    pre_step=step
    pre_start=last
    if start-step*MAX_CHAR>last:
        pre_start=start-step*MAX_CHAR
    else:
        pre_step=(last-start)/MAX_CHAR

    for i in range(1,MAX_CHAR):
        text=long[:i]
        offx=(MAX_CHAR-i)*CHAR_SIZE
        t=pre_start+(i*pre_step)
        alpha=i*ALPHA_STEP
        yield t,text,offx,alpha
        for j in range(1,CHAR_SPLIT):
            yield (pre_step/CHAR_SPLIT)*j+t,text,offx-(CHAR_SIZE/CHAR_SPLIT*j),alpha

    i=0
    while i<l:
        if l-i>MAX_CHAR:
            text=long[i:i+MAX_CHAR]
        else:
            text=long[i:]
        if i>0:
            for j in range(1,CHAR_SPLIT):
                yield i*step+start-(step/CHAR_SPLIT*j),text,CHAR_SIZE/CHAR_SPLIT*j,0

        yield i*step+start,text,0,0
        i+=1

def withlongline(lrc:lyrics)->lyricsOffsetX:
    ls=list(lrc)
    for i,v in enumerate(ls):
        if len(v[1])>MAX_CHAR and i+1<len(ls):
            start=v[0]
            stop=ls[i+1][0]
            last=0
            if i>0:
                last=ls[i-1][0]
            for k,v,off,alpha in genlongline(last,start,stop,v[1]):
                yield k,v,off,alpha
        else:
            yield v[0],v[1],0,0

def writetoml(lrc:lyrics,toml_path:str,offset:float=None):
    if offset==None:
        try:
            num=int(os.path.basename(toml_path).split("_")[0])
            offset=find_offset(num)
            if offset!=0:
                print("writing with auto found offset %f"%offset)
        except:
            offset=0
    else:
        offset=0
    if type(lrc)==dict:
        lrc=lrc.items()
    if os.path.exists(toml_path):
        if not ask_yes_no("%s exists, overwrite?"%toml_path):
            return
    with open(toml_path, 'w', encoding='utf-8') as f:
        f.write("lyrics = [\n")
        for k,v,offx,alpha in lrc:
            k=k+offset
            if k<0:
                continue
            if alpha!=0:
                alpha=f' color = "FFFFFF{alpha:02X}",'
            else:
                alpha=""
            f.write(f'    {{time = {format_time(k*100000)}, text = "{v.replace('"',r'\"')}", offset_x = {offx},{alpha} alignment = 1.0 }},\n')
        f.write("]\n")
    print('write to file "%s"'%toml_path)



if __name__=="__main__":
    it=read_lrc(sys.argv[1])
    out=gettomlpath(sys.argv[2])
    offset=None
    if len(sys.argv)>3:
        offset=float(sys.argv[3])
    writetoml(withlongline(it),out,offset)
    