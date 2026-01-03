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


def matcheng(line:str,part:str)->bool:
    parts=part.split()
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
        if len(line)==0 and (len(parts)==0 or (len(parts)==1 and parts[0]=="")):
            print(idx,os.path.join(dist,file))
            yield (file,"")
            idx+=1
            continue
        for part in parts:
            if part in blacklist:
                continue
            if len(part)<2 and not is_contains_kanji(part):
                continue
            lower=line.lower()
            if part.isascii() and lower.isascii():
                if matcheng(lower,part):
                    print(idx,os.path.join(dist,file),line,"("+part+")")
                    yield (file,line)
                    idx+=1
                    break
                else:
                    continue
            if part in lower:
                print(idx,os.path.join(dist,file),line,"("+part+")")
                yield (file,line)
                idx+=1
                break

def getdict2()->Generator[tuple[float,str]]:
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

def dict_to_srt(d: Generator[tuple[float,str]], filename: str):
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



lines_lrc='''オシエテ Mr.Wonder　見たことの無い世界
キミが語りだす　お伽の国の話
手を取って･･･　連れてってほしい
そう今夜　take on me

仲良しグループ　不意に一言
「恋をしてるの？」　わかるものなのね
さわやかなそよ風　目を瞑れば浮かぶ
そう　いたずらなその Smile

Hey DJ! don’t stop the music forever.
With you, I wanna be dancing on the floor.
Hey DJ! don’t stop the music forever.
心躍る二人 Irie に Lovin’

ミツメテ Mr.Wonder　まばゆい虹のヒカリ
波は法線上で　ビートに響きわたる
手を取って･･･　連れてってほしい
ココナッツの甘い香り　キミのファンタジックなキセキ

時を止めちゃうようなキセキ

キミが見せてくれる素敵な景色
いつだって新しい気持ちにさせて
パステルピンクの雲を追い越していく
ねえ　ずっと一緒にいたいよ

抱きしめてよ　もっと　強く
キミじゃなくちゃ　わたしダメなんだ
離さないで　ずっと　強く
そこらへんに落っこちてるはずの魔法
私には見つけられないの

オシエテ Mr.Wonder　見たことの無い世界
キミが語りだす　お伽の国の話
手を取って･･･　連れてってほしい
本当は　恐いんだ　夢が醒めるのが

ミツメテ Mr.Wonder　まばゆい虹のヒカリ
波は法線上で　ビートに響きわたる
手を取って･･･　連れてってほしい
ココナッツの甘い香り　キミのファンタジックなキセキ

時を止めちゃうようなキセキ 
'''
blacklist=[
    "ない",
    "人",
    "って",
    "した",
    "だっ",

]


fps=29.97
if __name__=="__main__":
    d=list(getdict2())
    if len(sys.argv)<2:
        dict_to_srt(d,"1.srt")
        writetoml(d,"1.toml")
    else:
        writetoml(d,os.path.join(lyrics_outdir,"%s_jp.toml"%sys.argv[1]))