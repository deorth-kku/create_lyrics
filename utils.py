
import os
from collections.abc import Generator
from pydiva.util.divatime import DivaTime

lyrics=Generator[tuple[float,str]]
lyricsOffsetX=Generator[tuple[float,str,float,int]]

def conv_pv_num(pv:str)->int:
    if pv.startswith("pv_"):
        return int(pv[3:])
    else:
        return int(pv)

def ask_yes_no(prompt: str) -> bool:
    """询问用户 (y/n)，返回 True 或 False。"""
    while True:
        ans = input(f"{prompt} (y/n): ").strip().lower()
        if ans in {"y", "yes"}:
            return True
        elif ans in {"n", "no"}:
            return False
        print("please enter y or n")

def ask_for_num(prompt: str) -> int:
    while True:
        ans = input(f"{prompt}: ").strip().lower()
        try:
            num=int(ans)
        except:
            print("please enter a number")
        else:
            return num

from config import mod_dir
from pydiva import pydsc


def read_offset(file:str)->float:
    time=0
    with open(file, 'rb') as stream:
        # Skip signature
        stream.seek(4)
        # Read all commands
        ops = pydsc.from_stream(stream, game_hint='FT')
        for op in ops:
            if op.op_name == 'MUSIC_PLAY':
                return float(time)
            elif op.op_name == 'TIME':
                time=float(op.param_values[0])/100000
    return time   
    

def find_offset(num:int)->float:
    
    for dir in os.listdir(mod_dir):
        dir=os.path.join(mod_dir,dir)
        if not os.path.isdir(dir):
            continue
        dsc=os.path.join(dir,"rom","script","pv_%03d_extreme.dsc"%num)
        if not os.path.exists(dsc):
            continue
        return read_offset(dsc)
    return 0


def format_time(ticks: DivaTime) -> str:
    # 每个 tick = 1/100000 秒
    total_seconds = ticks / 100000
    
    hours = int(total_seconds // 3600)
    total_seconds %= 3600
    minutes = int(total_seconds // 60)
    total_seconds %= 60
    
    seconds = int(total_seconds)
    fraction = int((total_seconds - seconds) * 100000)
    
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{fraction:05d}"


def format_float(f:float)->str:
    return format_time(f*100000)
    