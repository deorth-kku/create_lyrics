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

lines_lrc='''鬼蜘蛛一族狐に攫われ
悠久の苦痛耐え忍んできた
許さん許さん許さん許さん
命を乞うなぞさらさらしないが
百代先まで怨んでやろうぞ
貴様ら鬼だろ本物になれや
鬼蜘蛛化かした狐を喰っちゃれ
人喰いの末路私は知ってる

今宵は月夜間奴隷の悲鳴を
観賞している大名様たち
さぁさぁ、ようこそおいでぇなすって
高貴な見世物準備はいいかな？

ああああああああ…
奴隷の叫びは井戸の奥にまで
死なない程度にお前をいたぶる
私の眼を見ろ「命をやろうか？」

ああああああああああああああああああああああ…
私を許してどうか殺さずに　
お家へ返してほんとに痛いの

ああああああああああああああああああああああ…
痛いの痛いの痛いの痛いの
#あああああああああああ…
鬼蜘蛛一族狐に攫われ
悠久の苦痛耐え忍んできた
許さん許さん許さん許さん
命を乞うなぞさらさらしないが
百代先まで怨んでやろうぞ
貴様ら鬼だろ本物になれや
鬼蜘蛛化かした狐を喰っちゃれ
人喰いの末路私は知ってる

綺麗な指先生爪ひん剥き
指の関節をペンチで潰そう
方耳落としてお前にキスする
痛いか？痛いか？もっと泣き叫べ
客は歓ぶぞ興奮している
そろそろ終盤お前の解体
五月の黄泉沼死体の踊り場
晒したハラワタ蛆虫みたいね
ああああああああ…
私を許して鬼の感情は
戻れぬ自分へ見せしめついでさ
ああああああああ…
人を殺すたび私は濡れてる許して許して
#あああああああああ

#私の苦しみお前にわかるか
#私の悲しみお前にわかるか…
私は死んだの？何も感じない
屍抱きしめ後悔している
うっすら貴様の顔がまだ見える
一人で股座いじくり感じる
こいつの頭は蛆虫沸いてる
溶けた屍は蛆も集らずに
私の体に気安く触るな
気持ちいい気持ちいいはあぁ…

#終わりも近づき死にかけの君の
#臓物引きずりだしてあげましょ？
#お腹を拡げりゃ、桃色渦巻き
#悲鳴も聞こえず放心状態。
#ヌルヌルしていて錆びた釘の味。
#ゾクゾクしてきて、イってしまいそう。
#もう死んだかしら？断末魔の時。
#私を呪って死んでいきなさい。
鬼蜘蛛一族狐に攫われ
悠久の苦痛耐え忍んできた
許さん許さん許さん許さん
#命を乞うなぞさらさらしないが
百代先まで怨んでやろうぞ
貴様ら鬼だろ本物になれや
鬼蜘蛛化かした狐を喰っちゃれ
人喰いの末路私は知ってる
鬼蜘蛛一族狐に攫われ
悠久の苦痛耐え忍んできた
許さん許さん許さん許さん
命を乞うなぞさらさらしないが
百代先まで怨んでやろうぞ
貴様ら鬼だろ本物になれや
鬼蜘蛛化かした狐を喰っちゃれ
人喰いの末路私は知ってる

僕ハボウフラ君ノ傷ヲ
蛆虫ノヨウニグチュグチュト啜ル
愛シテ愛シテ愛シテ愛シテ
何ダカ体ガ熱クナッテキタ
僕ハボウフラ君ノ傷ヲ
蛆虫ノヨウニグチュグチュト啜ル
愛シテ愛シテ愛シテ愛シテ
何ダカスゴク興奮シテキタ
私もついに焼きが回ったのか
殺したお前らが迎えに来てる
私のお腹を拡げるつもりか？
#どうぞご自由にさっさと殺して
私は異常？こんな時にでも
濡れてしまうの痛いの待ってる
私の体は断末魔の時
さぁさぁ、ようこそ鬼畜のどつぼへ
鬼蜘蛛一族狐に攫われ
悠久の苦痛耐え忍んできた
許さん許さん許さん許さん
#命を乞うなぞさらさらしないが
百代先まで怨んでやろうぞ
貴様ら鬼だろ本物になれや
鬼蜘蛛化かした狐を喰っちゃれ
人喰いの末路私は知ってる
私の恨みでお前ら一族
死んでも解けない鬼蜘蛛の恨み
私を永遠崇めろ讃えろ
さもなくばお前を呪い殺すぞ
人間を食べるその異常な事
#代々続けろさもなくば殺す
鬼蜘蛛化かした狐を喰っちゃれ
人喰いの末路私は知ってる
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

]


fps=30
if __name__=="__main__":
    d=list(getdict2())
    if len(sys.argv)<2:
        dict_to_srt(d,"1.srt")
        writetoml(d,"1.toml")
    else:
        writetoml(d,os.path.join(lyrics_outdir,"%s_jp.toml"%sys.argv[1]),0.000001)