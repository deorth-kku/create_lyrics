"""Quick verification of offset."""
import sys
import os
from io import BytesIO
sys.path.insert(0, r'c:\Users\deort\Documents\create_lyrics')
from pydiva import pydsc

def check_offset(input_file, output_file):
    """Compare TIME values between input and output."""
    
    with open(input_file, 'rb') as f:
        raw_in = f.read()
    with open(output_file, 'rb') as f:
        raw_out = f.read()
    
    stream_in = BytesIO(raw_in)
    stream_in.read(4)
    ops_in = pydsc.from_stream(stream_in, game_hint='FT')
    
    stream_out = BytesIO(raw_out)
    stream_out.read(4)
    ops_out = pydsc.from_stream(stream_out, game_hint='FT')
    
    # Find MUSIC_PLAY
    mp_in = next(i for i, op in enumerate(ops_in) if op.op_name == 'MUSIC_PLAY')
    mp_out = next(i for i, op in enumerate(ops_out) if op.op_name == 'MUSIC_PLAY')
    
    print(f"MUSIC_PLAY: input={mp_in}, output={mp_out}")
    
    # Compare first 10 TIME ops after MUSIC_PLAY
    print("\nFirst 10 TIME ops after MUSIC_PLAY:")
    print(f"{'Idx':<6} {'Input':<15} {'Output':<15} {'Diff':<10}")
    
    in_times = [(i, ops_in[i].param_values[0]) for i in range(mp_in, len(ops_in)) if ops_in[i].op_name == 'TIME']
    out_times = [(i, ops_out[i].param_values[0]) for i in range(mp_out, len(ops_out)) if ops_out[i].op_name == 'TIME']
    
    for k in range(min(10, len(in_times))):
        idx_in, val_in = in_times[k]
        idx_out, val_out = out_times[k]
        diff = val_out - val_in
        print(f"{idx_in:<6} {val_in:<15} {val_out:<15} {diff:<10}")
    
    # Verify all offsets
    print("\nVerifying all TIME ops after MUSIC_PLAY...")
    errors = 0
    total = 0
    in_time_idx = 0
    out_time_idx = 0
    
    # Find all TIME ops after MUSIC_PLAY in both files
    in_times = [(i, ops_in[i].param_values[0]) for i in range(mp_in, len(ops_in)) if ops_in[i].op_name == 'TIME']
    out_times = [(i, ops_out[i].param_values[0]) for i in range(mp_out, len(ops_out)) if ops_out[i].op_name == 'TIME']
    
    print(f"Input TIME ops after MUSIC_PLAY: {len(in_times)}")
    print(f"Output TIME ops after MUSIC_PLAY: {len(out_times)}")
    
    for idx_in, val_in in in_times:
        if out_time_idx < len(out_times):
            idx_out, val_out = out_times[out_time_idx]
            diff = val_out - val_in
            if diff != -100000:
                print(f"ERROR at input idx {idx_in}: expected diff 100000, got {diff} (out idx {idx_out})")
                errors += 1
            out_time_idx += 1
            total += 1
    
    print(f"\nTotal TIME ops after MUSIC_PLAY: {total}")
    print(f"Errors: {errors}")

if __name__ == '__main__':
    check_offset(
        r'c:\Users\deort\Documents\create_lyrics\temp\pv_285_extreme_m39s.dsc',
        r'c:\Users\deort\Documents\create_lyrics\temp\pv_285_extreme_m39s_offset.dsc'
    )
