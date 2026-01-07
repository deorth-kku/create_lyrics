from pydiva import pydsc
from pydiva.util.divatime import DivaTime
from mml import diva_db_file
import os,sys


def extract_timestamps(file:str)->dict[DivaTime,int]:
    ops = []
    with open(file, 'rb') as stream:
        # Skip signature
        stream.seek(4)
        # Read all commands
        ops = pydsc.from_stream(stream, game_hint='FT')
    
    time=DivaTime(0)
    offset=DivaTime(0)
    m={}
    for op in ops:
        if op.op_name == 'TIME':
            time=op.param_values[0]
        elif op.op_name == 'LYRIC':
            m[time-offset]=op.param_values[0]
        elif op.op_name == 'MUSIC_PLAY':
            offset=time
    return m
            

from config import mod_dir
from utils import conv_pv_num,lyrics
from typing_tube import gettomlpath,writetoml


def readdblrc(input_pv:int)->lyrics:
    db=dict()
    for dir in os.listdir(mod_dir):
        full=os.path.join(mod_dir,dir,r'rom\mod_pv_db.txt')
        if not os.path.exists(full):
            continue
        scriptfile=os.path.join(mod_dir,dir,r'rom\script\pv_%03d_extreme.dsc'%input_pv)
        if not os.path.exists(scriptfile):
            continue
        db:dict[str,str]=diva_db_file(full)
        db.readlines()
        if db.get("pv_%03d.lyric.001"%input_pv,None):
            break
    for k,v in extract_timestamps(scriptfile).items():
        k=k/100000
        if v==0:
            yield k,""
        else:
            yield k,db["pv_%03d.lyric.%03d"%(input_pv,v)]


def extract_timing(input_pv:int,output_pv:int):
    toml=gettomlpath(output_pv)
    writetoml(readdblrc(input_pv),toml)

if __name__ == '__main__':
    input_pv=conv_pv_num(sys.argv[1])
    if len(sys.argv)<3:
        output_pv=input_pv
    else:
        output_pv=conv_pv_num(sys.argv[2])
    extract_timing(input_pv,output_pv)
    