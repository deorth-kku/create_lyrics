from config import lyrics_outdir
from offset import readtoml
from utils import lyrics
from collections.abc import Generator
from typing_tube import format_float
import os
from tinytag import TinyTag
from mml import diva_db_file

TOLERANCE=0.2

def haserror(it:lyrics,songlen:float)->Generator[str]:
    last=0
    laststr=""
    for k,v in it:
        if k<last:
            yield "timestamp decrease at %s, last %s"%(format_float(k),format_float(last))
        last=k
        laststr=v
    if laststr!="":
        yield "didn't clear text at the end %s"%format_float(last)
    
    if last>songlen*(1+TOLERANCE) or last<songlen*(1-TOLERANCE):
        yield "song length didn't match: lrc:%s, ogg:%s"%(format_float(last),format_float(songlen))

def readogglen(file:str)->float:
    tag = TinyTag.get(file)
    duration = tag.duration 
    return duration

from config import mod_dir,custom_skip

def findogg(input_pv:int)->str:
    db=dict()
    for dir in os.listdir(mod_dir):
        if dir in custom_skip:
            continue
        dir=os.path.join(mod_dir,dir)
        full=os.path.join(dir,r'rom\mod_pv_db.txt')
        if not os.path.exists(full):
            continue
        db:dict[str,str]=diva_db_file(full)
        db.readlines()
        filename=db.get("pv_%03d.song_file_name"%input_pv,None)
        if filename==None:
            continue
        filename=os.path.join(dir,filename)
        if not os.path.exists(filename):
            continue
        return filename
    raise ValueError("cannot find ogg for pv_%03d"%input_pv)

if __name__== "__main__":
    for file in os.listdir(lyrics_outdir):
        pv_num=int(file.split("_")[0])
        file=os.path.join(lyrics_outdir,file)
        it=readtoml(file)
        ogglen=readogglen(findogg(pv_num))
        try:
            errs=list(haserror(it,ogglen))
        except Exception as e:
            print("%s has format error %s"%(file,e))
            continue
        if len(errs)!=0:
            print("%s has errors %s"%(file,errs))