from search_song import search_song
import sys
from pathlib import Path

if __name__ == '__main__':
    s=Path(sys.argv[1]).read_text(encoding="utf-8")
    for line in s.splitlines():
        line=line.strip()
        for dir,pvid,name in search_song(line):
            print(dir,pvid,name)
