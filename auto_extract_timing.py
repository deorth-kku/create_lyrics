
from has_lyrics import has_lyrics_all,has_lyrics
from extract_timing import extract_timing
from search_song import search_song
import os
from config import mod_dir
from utils import ask_yes_no,conv_pv_num
if __name__=="__main__":
    for dir,pv_code,songname in has_lyrics_all():
        for d,p,s in search_song(songname):
            if p==pv_code:
                continue
            scriptfile=os.path.join(mod_dir,d,r'rom\script\%s_extreme.dsc'%p)
            if not os.path.exists(scriptfile):
                print("cannot generate lyrics for (%s,%s,%s) from (%s,%s,%s), file %s do not exist"%(dir,pv_code,songname,d,p,s,scriptfile))
                continue
            if not has_lyrics(scriptfile):
                continue
            if not ask_yes_no("generate lyrics for (%s,%s,%s) from (%s,%s,%s)?"%(dir,pv_code,songname,d,p,s)):
                continue
            extract_timing(conv_pv_num(p),conv_pv_num(pv_code))
            break