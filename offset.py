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

if __name__ == "__main__":
    with open(sys.argv[1], "rb") as f:
        data = tomllib.load(f)
    for i in data["lyrics"]:
        t:time=i["time"]
        print(offset(t,float(sys.argv[2])))