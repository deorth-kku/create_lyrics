import os
import json
from collections.abc import Generator
import sys


def getlines(lines:str)->Generator[str]:
    for line in lines.split("\n"):
        yield line.strip()


from config import dist

from sudachipy import tokenizer
from sudachipy import dictionary

# 全局只创建一次 tokenizer（性能更好）
_tokenizer = dictionary.Dictionary().create(
    mode=tokenizer.Tokenizer.SplitMode.A  # A=粗粒度 / B=默认 / C=最细（常用）
)


def splitwords_to_list(input_text: list[str]) -> Generator[str]:
    for text in input_text:
        if text.isascii():
            if len(text)<=2 and len(text)!=0:
                continue
            for part in text.split(","):
                yield part.lower()
        elif len(text)<=3:
            yield text
        else:
            for m in _tokenizer.tokenize(text):
                t0=m.surface()
                if t0 in blacklist:
                    continue
                yield t0


import re

# 汉字范围（日语实际使用的汉字基本都在这个区间）
HAS_KANJI = re.compile(r'[\u4e00-\u9fff]')

def is_pure_kana(word: str) -> bool:
    """判断这个词是否「完全不含汉字」（可以包含假名、数字、英文、标点等）"""
    return not HAS_KANJI.search(word)


def is_contains_kanji(word: str) -> bool:
    """判断这个词是否「至少包含一个汉字」"""
    return bool(HAS_KANJI.search(word))


def matcheng(line:str,parts:list[str])->bool:
    if len(parts)==0:
        return False
    if len(parts)==1 and len(parts[0])<=3:
        return False
    m=0
    for p in parts:
        if p in line:
            m+=1
    return (m/len(parts))>0.5
    


def getdict()->Generator[list[str]]:
    lines=list(getlines(lines_lrc))
    idx=0
    for file in os.listdir(dist):
        if idx>=len(lines):
            break
        line=lines[idx]
        if line.startswith("#"):
            print(idx,"comment",line)
            idx+=1
            yield ("pass"+str(idx),line.lstrip("#"))


        if not file.endswith(".json"):
            continue
        with open(os.path.join(dist,file), 'r', encoding='utf-8') as f:
            data=json.load(f)
        
        scores:list[int]=data["rec_scores"]
        parts:list[str]=data["rec_texts"]
        for i,v in enumerate(scores):
            if v<0.7 and len(parts[i])<=2 and parts[i].isascii():
                parts[i]=""
            elif v<0.5 and len(parts[i])==1:
                parts[i]=""
        
        parts=list(splitwords_to_list(parts))
        if len(line)==0:
            if len(parts)==0 or (len(parts)==1 and parts[0]==""):
                print(idx,os.path.join(dist,file))
                yield (file,"")
                idx+=1
                continue
            else:
                continue
        
        parts=[p for p in parts if p!= "" ]
        if len(parts)==0:
            continue

        lower=line.lower()
        if lower.isascii() and matcheng(lower,parts):
            pass
        elif matchjpn(lower,parts):
            pass
        else:
            continue
        print(idx,os.path.join(dist,file),line,parts)
        idx+=1
        yield (file,line)

def hasascii(s:str)->bool:
    for p in s:
        if p.isascii():
            return True
    return False

def matchjpn(line:str,parts:list[str])->bool:
    if not hasascii(line):
        parts=[p for p in parts if not p.isascii() ]

    if len(parts)==0:
        return False
    m=0
    for p in parts:
        if p in blacklist:
            continue
        if p in line:
            m+=1
    return (m/len(parts))>0.5

from utils import lyrics
def getdict2()->lyrics:
    for k,v in getdict():
        k=k.lstrip("0").split("_")[0]
        try:
            k=int(k)-1 # ffmpeg %05d.png starts with 00001.png, bruh
        except:
            k=0
        k=k/fps
        yield (k,v)


from typing_tube import writetoml
from config import lyrics_outdir
from utils import lyrics

def dict_to_srt(d: lyrics, filename: str):
    """
    将 dict[float, str] 写成 srt 文件。
    key: 开始时间（秒，float）
    value: 字幕文本
    结束时间 = 下一条字幕的开始时间
    """
    def fmt(t: float) -> str:
        h = int(t // 3600)
        m = int((t % 3600) // 60)
        s = int(t % 60)
        ms = int(round((t - int(t)) * 1000))
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    items = sorted(d, key=lambda x: x[0])

    with open(filename, "w", encoding="utf-8") as f:
        for i, (start, text) in enumerate(items):
            if i + 1 >= len(items):
                break  # 最后一条没有结束时间，直接丢弃
            end = items[i + 1][0]

            f.write(f"{i + 1}\n")
            f.write(f"{fmt(start)} --> {fmt(end)}\n")
            f.write(f"{text}\n\n")

from offset import offsetgen

lines_lrc='''物語の終わりに
私のヒーローは死にました
最後の章の終わりに
あなたは死ぬことになった
私の過去の行動は、
私に反対しました
どうしようもなかった、
手は血まみれだった

今は大丈夫だ、
私は自分になることを
学びました

あなたを殺したのは私だった
私を信じるなんてばかだった
あなたを殺したのは私だった
私を信じるなんてばかだった

あなたを殺したのは私だった
私を信じるなんてばかだった
あなたを殺したのは私だった
私を信じるなんてばかだった

未知を忘れる、
世界を笑う
シミュレーションではないことを
毒を飲み込む、
今日も踊ろう
死ぬまで幸せに歌う
無に消えていく、
彼らは笑っている
しかし、彼らは無意味です
毒を飲み込む、
今日も踊ろう
死ぬまで幸せにー
今は大丈夫だ、
私は自分になることを
学びました

あなたを殺したのは私だった
私を信じるなんてばかだった
あなたを殺したのは私だった
愛してたけどあなたは悪かった 
'''
blacklist=[
    "ない",
    "人",
    "って",
    "した",
    "だっ",
    "て",
    "た",
    "に",
    "か",
    'の',
    'が',
    "は",
    "を",
    "だ",

    '私',
    "だっ",
    "終わり",
    "彼らは"
]


fps=29.97
if __name__=="__main__":
    d=list(getdict2())
    if len(sys.argv)<2:
        dict_to_srt(d,"1.srt")
        writetoml(d,"1.toml")
    else:
        writetoml(d,os.path.join(lyrics_outdir,"%s_jp.toml"%sys.argv[1]),0.000001)