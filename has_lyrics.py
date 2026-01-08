
from pydiva import pydsc
from config import mod_dir
import os
from mml import diva_db_file
from collections.abc import Generator


def has_lyrics(file:str)->bool:
    ops = []
    with open(file, 'rb') as stream:
        # Skip signature
        stream.seek(4)
        # Read all commands
        ops = pydsc.from_stream(stream, game_hint='FT')
    for op in ops:
        if op.op_name == 'LYRIC':
            return True
    return False
    
chart_suffix="_extreme.dsc"
chart_suffixlen=len(chart_suffix)


def has_lyrics_all()->Generator[tuple[str,str,str]]:
    toml_lrc=set()
    for dir in os.listdir(mod_dir):
        lrcdir=os.path.join(mod_dir,dir,"lyrics_eden")
        if not os.path.exists(lrcdir):
            continue
        for lrc in os.listdir(lrcdir):
            toml_lrc.add(lrc.split("_")[0].split(".")[0])
    for dir in os.listdir(mod_dir):
        full=os.path.join(mod_dir,dir,r'rom\mod_pv_db.txt')
        if not os.path.exists(full):
            continue
        scriptdir=os.path.join(mod_dir,dir,r'rom\script')
        if not os.path.exists(scriptdir):
            continue
        db:dict[str,str]=diva_db_file(full)
        db.readlines()
        for file in os.listdir(scriptdir):
            if not file.endswith("_extreme.dsc"):
                continue
            if has_lyrics(os.path.join(scriptdir,file)):
                continue
            pv_code=file[:-chart_suffixlen]
            if pv_code[3:] in toml_lrc:
                continue
            songname=db.get(pv_code+".song_name","???")
            yield (dir,pv_code,songname)

if __name__ == '__main__':
    with open("no_lrc.txt","w",encoding="utf-8") as f:
        for dir,pv_code,songname in has_lyrics_all():
            f.write("%s\t%s\t%s\n"%(dir,pv_code,songname))
            print(dir,pv_code,songname)
                