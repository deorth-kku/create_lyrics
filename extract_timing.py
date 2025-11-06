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
    m={}
    for op in ops:
        if op.op_name == 'TIME':
            time=op.param_values[0]
        elif op.op_name == 'LYRIC':
            m[time]=op.param_values[0]
    return m
            
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

from config import mod_dir,lyrics_outdir
from utils import conv_pv_num,ask_yes_no

def extract_timing(input_pv:int,output_pv:int):
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
    
    toml_path="%03d_jp.toml"%output_pv
    toml_path=os.path.join(lyrics_outdir,toml_path)
    if os.path.exists(toml_path):
        if not ask_yes_no("%s exists, overwrite?"%toml_path):
            sys.exit(1)
    
    with open(toml_path, 'w', encoding='utf-8') as f:
        f.write("lyrics = [\n")
        for k,v in extract_timestamps(scriptfile).items():
            if v==0:
                lrc=""
            else:
                lrc=db["pv_%03d.lyric.%03d"%(input_pv,v)]
            f.write(f'    {{time = {format_time(k)}, text = "{lrc}"}},\n')
        f.write("]\n")

if __name__ == '__main__':
    input_pv=conv_pv_num(sys.argv[1])
    if len(sys.argv)<3:
        output_pv=input_pv
    else:
        output_pv=conv_pv_num(sys.argv[2])
    extract_timing(input_pv,output_pv)
    