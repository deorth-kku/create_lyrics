
from pydiva import pydsc
from pydiva.util.divatime import DivaTime
from mml import diva_db_file



def extract_timestamps(file:str)->dict[DivaTime,int]:
    ops = []
    with open(file, 'rb') as stream:
        # Skip signature
        stream.seek(4)
        # Read all commands
        ops = pydsc.from_stream(stream, game_hint='FT')
    
    time=DivaTime(0)
    m={}
    for op in ops:
        if len(op.param_values)>0:
            print(op.op_name,op.param_values[0])
        else:
            print(op.op_name)
        if op.op_name == 'TIME':
            time=op.param_values[0]
        elif op.op_name == 'TARGET':
            m[time]=op.param_values[0]
    return m


if __name__== "__main__":
    d=extract_timestamps(r"F:\SteamLibrary\steamapps\common\Hatsune Miku Project DIVA Mega Mix Plus\mods\EdenMasochistEditPack\rom\script\pv_1268_extreme.dsc")
    for k,v in d.items():
        pass
        #print(k,v)