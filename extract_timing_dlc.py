from pydiva import pydsc
from pydiva.util.divatime import DivaTime
from mml import diva_db_file
import os,sys,re


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


def pv_num_of(dsc_file:str)->int:
    m=re.search(r'pv_(\d+)',os.path.basename(dsc_file))
    return int(m.group(1))


def readdblrc(db_file:str,dsc_file:str):
    pv=pv_num_of(dsc_file)
    db:dict[str,str]=diva_db_file(db_file)
    db.readlines()
    for k,v in extract_timestamps(dsc_file).items():
        k=k/100000
        if v==0:
            yield k,""
        else:
            yield k,db["pv_%03d.lyric.%03d"%(pv,v)]


from utils import lyrics
from typing_tube import writetoml


def extract_timing(db_file:str,dsc_file:str,output:str=None):
    if output is None:
        output="%d.toml"%pv_num_of(dsc_file)
    writetoml(readdblrc(db_file,dsc_file),output,offset=0)


if __name__ == '__main__':
    db_file=sys.argv[1]
    dsc_file=sys.argv[2]
    output=sys.argv[3] if len(sys.argv)>3 else None
    extract_timing(db_file,dsc_file,output)
