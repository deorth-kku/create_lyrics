import tomllib
from datetime import datetime, time, timedelta
import sys
from utils import lyrics



def offset(t:time,offset:float)->time:

    offset = timedelta(seconds=offset)


    dt = datetime.combine(datetime.today(), t)
    dt_offset:datetime = dt + offset
    return dt_offset.time()


def offsetgen(d:lyrics,offset:float)->lyrics:
    for k,v in d:
        yield k+offset,v

from toml2srt import readtoml
from typing_tube import writetoml
if __name__ == "__main__":
    it=readtoml(sys.argv[1])
    if len(sys.argv)==3:
        delta=float(sys.argv[2])
        it=dict(it)
        items = sorted(it.items(), key=lambda x: x[0])
        writetoml(items,sys.argv[1],delta)
    elif len(sys.argv)>3:
        delta=float(sys.argv[3])
        writetoml(it,sys.argv[2],delta)