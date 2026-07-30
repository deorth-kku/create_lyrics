"""
Offset TIME operations in a DSC file after MUSIC_PLAY.

Usage:
    python offset_times.py <input.dsc> <output.dsc> <offset>
    
    offset: number of ticks (1/100000 seconds) to add to each TIME after MUSIC_PLAY
"""
import sys
import os
from io import BytesIO

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pydiva import pydsc

def offset_dsc_times(input_file: str, output_file: str, offset: int) -> None:
    """
    Read a DSC file, offset all TIME operations after MUSIC_PLAY by the given amount,
    and write to a new file.
    """
    print(f"Reading: {input_file}")
    
    # Read the file
    with open(input_file, 'rb') as f:
        raw = f.read()
    
    # Parse ops
    stream = BytesIO(raw)
    # Skip 4-byte signature
    stream.read(4)
    ops = pydsc.from_stream(stream, game_hint='FT')
    stream.close()
    
    print(f"Parsed {len(ops)} operations")
    
    # Find MUSIC_PLAY index
    music_play_idx = None
    for i, op in enumerate(ops):
        if op.op_name == 'MUSIC_PLAY':
            music_play_idx = i
            break
    
    if music_play_idx is None:
        print("ERROR: MUSIC_PLAY not found in DSC file")
        return
    
    print(f"MUSIC_PLAY found at index {music_play_idx}")
    
    # Count TIME ops before and after
    time_before = sum(1 for i, op in enumerate(ops[:music_play_idx]) if op.op_name == 'TIME')
    time_after = sum(1 for i, op in enumerate(ops[music_play_idx:]) if op.op_name == 'TIME')
    
    print(f"TIME ops before MUSIC_PLAY: {time_before}")
    print(f"TIME ops after MUSIC_PLAY: {time_after}")
    
    # Offset TIME operations after MUSIC_PLAY
    offset_count = 0
    for i in range(music_play_idx, len(ops)):
        op = ops[i]
        if op.op_name == 'TIME':
            # TIME has one param: the time value in ticks
            old_time = op.param_values[0]
            op.param_values[0] = old_time + offset
            offset_count += 1
            if offset_count <= 5 or offset_count == time_after:
                print(f"  [{i}] TIME: {old_time} -> {op.param_values[0]} (offset={offset})")
    
    print(f"Offset {offset_count} TIME operations")
    
    # Write to output file
    print(f"Writing to: {output_file}")
    
    # Write ops directly (without extra header from to_stream)
    with open(output_file, 'wb') as f:
        # Write 4-byte signature
        f.write(raw[:4])
        # Write each op directly
        for op in ops:
            op.write_to_stream(f)
    
    print(f"Done! Output written to {output_file}")
    print(f"Output file size: {os.path.getsize(output_file)} bytes")


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    offset = int(sys.argv[3])
    
    offset_dsc_times(input_file, output_file, offset)
