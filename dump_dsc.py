
from pydiva import pydsc
import sys

def dump(file:str)->None:
    with open(file, 'rb') as stream:
        # Skip signature
        stream.seek(4)
        # Read all commands
        ops = pydsc.from_stream(stream, game_hint='FT')
        for op in ops:
            print(op.op_name,op.param_values)

if __name__ == "__main__":
    dump(sys.argv[1])