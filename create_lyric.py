from pydiva import pydsc
import sys

TARGET_TYPE_CIRCLE = 1
TARGET_TYPE_CROSS = 2
TARGET_TYPE_SQUARE = 3

def main():
    ops = []
    with open(sys.argv[1], 'rb') as stream:
        # Skip signature
        stream.seek(4)
        # Read all commands
        ops = pydsc.from_stream(stream, game_hint='FT')
    
    lyricsData = []
    flyingTime = 0
    time = 0
    lyricIndex = 0
    for op in ops:
        if (op.op_name == 'TIME'):
            time = op.param_values[0]
        elif (op.op_name == 'TARGET'):
            # Handle lyric conversion
            if (op.param_values[0] == TARGET_TYPE_CROSS):
                # Append time command to the lyric output list
                lyricsData.append(pydsc.DscOp.from_name(game='FT', op_name='TIME', param_values=[time + flyingTime]))
                lyricsData.append(pydsc.DscOp.from_name(game='FT', op_name='LYRIC', param_values=[0, -1]))
            elif (op.param_values[0] == TARGET_TYPE_CIRCLE):
                # Append time command to the lyric output list
                lyricsData.append(pydsc.DscOp.from_name(game='FT', op_name='TIME', param_values=[time + flyingTime]))
                lyricIndex += 1;
                lyricsData.append(pydsc.DscOp.from_name(game='FT', op_name='LYRIC', param_values=[lyricIndex, -1]))
            elif (op.param_values[0] == TARGET_TYPE_SQUARE):
                # Append time command to the lyric output list
                lyricsData.append(pydsc.DscOp.from_name(game='FT', op_name='TIME', param_values=[time + flyingTime]))
                lyricsData.append(pydsc.DscOp.from_name(game='FT', op_name='LYRIC', param_values=[lyricIndex, -1]))
        elif (op.op_name == 'TARGET_FLYING_TIME'):
            flyingTime = op.param_values[0] * 100 # Convert to seconds
    
    # Add end command
    lyricsData.append(pydsc.DscOp.from_name(game='FT', op_name='END', param_values=[]))
    
    with open(sys.argv[1].split('.')[0] + '_lyric.dsc', 'wb') as stream:
        pydsc.to_stream(lyricsData, stream)

if __name__ == '__main__':
    main()