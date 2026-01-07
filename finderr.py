from config import lyrics_outdir
from offset import readtoml
from utils import lyrics
from collections.abc import Generator
from typing_tube import format_float
import os

def has_order_error(it:lyrics)->Generator[str]:
    last=0
    laststr=""
    for k,v in it:
        if k<last:
            yield "timestamp decrease at %s, last %s"%(format_float(k),format_float(last))
        last=k
        laststr=v
    if laststr!="":
        yield "didn't clear text at the end %s"%format_float(last)




if __name__== "__main__":
    for file in os.listdir(lyrics_outdir):
        file=os.path.join(lyrics_outdir,file)
        it=readtoml(file)
        try:
            errs=list(has_order_error(it))
        except Exception as e:
            print("%s has format error %s"%(file,e))
            continue
        if len(errs)!=0:
            print("%s has errors %s"%(file,errs))