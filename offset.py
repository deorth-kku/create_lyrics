import tomllib
from datetime import datetime, time, timedelta
import sys

def offset(t:time,offset:float)->time:

    offset = timedelta(seconds=offset)


    dt = datetime.combine(datetime.today(), t)
    dt_offset:datetime = dt + offset
    return dt_offset.time()

if __name__ == "__main__":
    with open(sys.argv[1], "rb") as f:
        data = tomllib.load(f)
    for i in data["lyrics"]:
        t:time=i["time"]
        print(offset(t,-0.57142))