import os
import json
from collections.abc import Generator



def getlines(lines:str)->Generator[str]:
    for line in lines.split("\n"):
        yield line.strip()


source=r"E:\ocr\source"
dist=r"E:\ocr\dst"


from sudachipy import tokenizer
from sudachipy import dictionary

# 全局只创建一次 tokenizer（性能更好）
_tokenizer = dictionary.Dictionary().create(
    mode=tokenizer.Tokenizer.SplitMode.A  # A=粗粒度 / B=默认 / C=最细（常用）
)

blacklist=[
    "まま",
    "ない",
    "れない",
    "って",
    "じゃ",
    "ねー",
    "もう",
    "ガラス",
    "きみ",
    "場",
    "世",
    "感",
    "中",
    "待",
    "会い",
    "来"
]

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



lines_lrc='''ハロウィンがやってきた
お気に入りのもので飾り付けて
蛍光灯割ってスタンドを蹴って
暗闇に紛れるお化けもどき
ああ　テンションあげよう！
今日は不思議ちゃんデーです
ポジティブシンキングで嫌なことはバイバイ
カボチャをくり抜いて火を灯せ！

魔女に仮装して　街を出歩こう
恐怖におびえる子供たちよ
さあ叫べ！さあ叫べ！

さあ私の手をとって　扉を蹴って　外へと飛び出そうぜ
たくさん溢れるお菓子求め　あっちこっち行ったり来たりで
さあ君の夢を追って　走り回って　何度も繰り返そうぜ
理想が現実になる　長い長いハロウィンは始まった！

お化けがやってくる
夜な夜なパレードが開幕する
ジャックランタンは常にそばに
終わらない一日の始まりを忘れたころに君は現れる
どこからかその姿ふいに見せて消える

クリスマスがやってくる
お気に入りのもので飾り付けて
ソリ引っ張りだして　たくさんプレゼントのせて
雪降り積もる街に飛び出そう
寒さ吹っ飛ばせ！
サンタクロースお呼びです
トナカイ引っ張っちゃって空飛んじゃってもいいかい？
クリスマスツリーに火を灯せ！

プレゼントの中に隠した仕掛け
開けてしまった子供たちよ
さあ叫べ！さあ叫べ！さあ喚け！さあ喚け！
ハロウィンは終わらない　恐怖のクリスマスのはじまりはじまり！

楽しいことずっと続けようぜ
好奇心はきっと抑えきれない！
少しの出来心ぐらい許してもらえるはずさ
そうやって人生を楽しもう
ほらみんなで
さあ叫べ！さあ叫べ！さあ叫べ！さあ叫べ！

さあ私の手握って　ほらつかまって　空へと飛び立とうぜ
クリスマスの夜はまだ長い　もっとずっと遊びたい
ほら横隔膜で笑って　片足つって　キョトン顔を笑った
これはクリスマスであり　ハロウィン　ハロウィン　365日
さあ私の手をとって　扉を蹴って　外へと飛び出そうぜ
たくさん溢れる笑顔求め　あっちこっち行ったり来たりで
さあ君の夢を追って　走り回って　何度も繰り返そうぜ
理想が現実になる　長い長いハロウィンはずっと終わらない 
'''


def getdict2()->Generator[tuple[float,str]]:
    for k,v in getdict():
        k=k.lstrip("0").split("_")[0]
        try:
            k=int(k)
        except:
            k=0
        k=k/fps
        yield (k,v)


from typing_tube import writetoml
from config import lyrics_outdir

fps=25
if __name__=="__main__":
    d=list(getdict2())
    #dict_to_srt(d,"1.srt")
    #writetoml(d,"1.toml")
    writetoml(d,os.path.join(lyrics_outdir,"1268_jp.toml"))