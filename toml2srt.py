import tomllib
from datetime import datetime, time, timedelta
import sys
from collections.abc import Generator
from utils import lyrics

def time_to_float(t: time) -> float:
    return (
        t.hour * 3600
        + t.minute * 60
        + t.second
        + t.microsecond / 1_000_000
    )


def readtoml(file:str)->lyrics:
    with open(file, "rb") as f:
        data = tomllib.load(f)
    for i in data["lyrics"]:
        yield time_to_float(i["time"]),i["text"]

from paddle2 import dict_to_srt

if __name__=="__main__":
    gen=readtoml(sys.argv[1])
    dict_to_srt(gen,"1.srt")