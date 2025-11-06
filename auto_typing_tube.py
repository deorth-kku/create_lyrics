from typing_tube import net_search_song,writetoml,getlrc,parse_file
from has_lyrics import has_lyrics_all
import os
from utils import conv_pv_num,ask_for_num
from config import lyrics_outdir

if __name__ == "__main__":
    for dir,pv_name,songname in has_lyrics_all():
        songlist=net_search_song(songname)
        if len(songlist)==0:
            print("cannot find (%s) in typing-tube"%songname)
            continue
        elif len(songlist)>1:
            mapdict={}
            index=1
            for num,ti in songlist.items():
                print("%d\t%s"%(index,ti))
                mapdict[index]=num
                index+=1
            index=ask_for_num("please select a title")
            if index==0:
                print("skipping (%s,%s,%s)"%(dir,pv_name,songname))
                continue
            tt_id:str=mapdict[index]
        else:
            tt_id=next(iter(songlist))
        
        _,lrc=parse_file(getlrc(tt_id))
        toml_path=os.path.join(lyrics_outdir,"%d_jp.toml"%conv_pv_num(pv_name))
        writetoml(lrc,toml_path)
        print("write lrc for (%s,%s,%s)"%(dir,pv_name,songname))