"""
Find the time of the first TARGET operation in a DSC file.

Usage:
    python find_target_time.py <file.dsc>
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pydiva import pydsc

def find_target_time(file: str) -> float:
    """
    Find the time of the first TARGET operation in a DSC file.
    Returns the time in seconds (float).
    """
    print(f"Reading: {file}")
    
    time = 0
    with open(file, 'rb') as stream:
        # Skip signature
        stream.seek(4)
        # Read all commands
        ops = pydsc.from_stream(stream, game_hint='FT')
        
        for op in ops:
            if op.op_name == 'TARGET':
                print(f"Found TARGET at index {ops.index(op)}")
                print(f"Time: {time / 100000} seconds ({time} ticks)")
                return time / 100000
            elif op.op_name == 'TIME':
                time = int(op.param_values[0])
    
    print("No TARGET found in DSC file")
    return -1


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    
    file = sys.argv[1]
    result = find_target_time(file)
    
    if result >= 0:
        print(f"First TARGET time: {result:.5f} seconds ({int(result * 100000)} ticks)")
    else:
        print("First TARGET time: -1 (not found)")
