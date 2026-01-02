from mml import diva_db_file

from config import mod_dir
import os

if __name__ == "__main__":
    f2db=os.path.join(mod_dir,r"X Song Pack\rom\mod_pv_db.txt")
    f2db=diva_db_file(f2db)
    edendb=os.path.join(mod_dir,r"Another Song Merge Tool\rom\mod_pv_db.txt")
    edendb:dict=diva_db_file(edendb)
    commit=set()
    for k in f2db:
        if k.startswith('commit'):
            continue
        commit.add(k.split(".")[0])

    lastcommitnum=edendb.commit
    new=diva_db_file(os.path.join(mod_dir,r"fix F2nd Hoshikuzu Vanilla\rom\mod_pv_db.txt"))

    for k,v in edendb.items():
        k:str
        if k.split(".")[0] in commit:
            lastcommitnum+=1
            new["commit%05d"%lastcommitnum]= k+"="+v
        elif k.endswith("date"):
            new[k]="20251231"
        else:
            new[k]=v

    
    new.write_file()