
import os
from collections.abc import Generator


lyrics=Generator[tuple[float,str]]

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