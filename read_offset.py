from utils import read_offset
import sys

if __name__=="__main__":
    off=read_offset(sys.argv[1])
    print(off)