from mml import diva_db_file
import os,sys
from collections.abc import Generator

from config import mod_dir

def search_song(name:str)->Generator[tuple[str,str,str]]:
    for dir in os.listdir(mod_dir):
        full=os.path.join(mod_dir,dir,r'rom\mod_pv_db.txt')
        if os.path.exists(full):
            db:dict[str,str]=diva_db_file(full)
            db.readlines()
            for k,v in db.items():
                if k.endswith("song_name") and name in v:
                    yield dir,k.split(".")[0],v


if __name__ == '__main__':
    for dir,pvid,name in search_song(sys.argv[1]):
        print(dir,pvid,name)
