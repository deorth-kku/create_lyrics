import re,sys
from utils import lyrics
from paddle2 import writetoml


time_re = re.compile(r"\[(\d+):(\d+(?:\.\d+)?)\]")

def read_lrc(path: str) -> lyrics:
    """
    读取 lrc 文件，返回 dict[float, str]
    key 为秒级时间戳（float），value 为歌词文本
    """
    
    result: dict[float, str] = {}

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            matches = time_re.findall(line)
            if not matches:
                continue

            # 去掉所有时间标签后剩下的就是歌词
            text = time_re.sub("", line).strip()
            if not text:
                continue

            for m, s in matches:
                ts = int(m) * 60 + float(s)
                result[ts] = text

    return result.items()

from typing_tube import gettomlpath

if __name__=="__main__":
    it=read_lrc(sys.argv[1])
    out=gettomlpath(sys.argv[2])
    offset=None
    if len(sys.argv)>3:
        offset=float(sys.argv[3])
    writetoml(it,out,offset)