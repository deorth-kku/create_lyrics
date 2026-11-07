"""
推迟 DSC 文件中 MUSIC_PLAY 事件的发生时间，但不移动其它任何事件。

DSC 中一个 TIME 会作用于它之后、直到下一个 TIME 之前的所有事件，
因此这些事件“共享同一个 TIME”。

两种情况：

  A) MUSIC_PLAY 是它所在 TIME 组里唯一的事件（没和别人共享）：
        TIME [DivaTime(0)]
        MUSIC_PLAY []
        TIME [DivaTime(338600)]
     直接把该 TIME 的值改成 原值 + OFFSET 即可，不用新增 TIME：
        TIME [DivaTime(OFFSET)]
        MUSIC_PLAY []
        TIME [DivaTime(338600)]

  B) MUSIC_PLAY 和别的事件共享同一个 TIME：
        TIME [DivaTime(0)]
        CHANGE_FIELD [1]
        MUSIC_PLAY []
        MOVIE_PLAY [True]
        MOVIE_DISP [1]
        TIME [DivaTime(338600)]
     不能直接改 TIME 值（会连带移动其它事件）。需要：
       1. 找到“与 MUSIC_PLAY 共享同一 TIME 的最后一个事件”（本例是 MOVIE_DISP，
          即该 TIME 组里最后一个事件，不是写死的）
       2. 在它之后新建一个 TIME，值 = 原 TIME 值 + OFFSET
       3. 把 MUSIC_PLAY 从原位置移除，并移到新建 TIME 的后面
     结果：
        TIME [DivaTime(0)]
        CHANGE_FIELD [1]
        MOVIE_PLAY [True]
        MOVIE_DISP [1]
        TIME [DivaTime(OFFSET)]
        MUSIC_PLAY []
        TIME [DivaTime(338600)]

用法：
    python delay_music_play.py <input.dsc> <output.dsc> <offset>

    offset 单位是 DivaTime（1 秒 = 100000）。例如推迟 1 秒就传 100000。
    如果 output 传 "-" 则原地覆盖 input。
"""

import sys
from io import BytesIO

from pydiva import pydsc
from pydiva.pydsc import DscOp


def _parse_offset(text):
    """把 offset 参数解析为整数（DivaTime 单位）。支持 'i123' / '123' / 负数。"""
    t = text.strip()
    if t.startswith('i'):
        t = t[1:]
    return int(t)


def _group_end(ops, time_idx):
    """
    返回 time_idx 这个 TIME 所管辖的“组”的结束边界（不含该边界）。
    边界是 time_idx 之后最近的下一个 TIME，若没有则到 END(op_id==0) 为止。
    """
    end_idx = next(i for i, op in enumerate(ops) if op.op_id == 0)
    group_end = end_idx
    for k in range(time_idx + 1, end_idx):
        if ops[k].op_name == 'TIME':
            group_end = k
            break
    return group_end


def delay_music_play(input_path, output_path, offset):
    with open(input_path, 'rb') as f:
        data = f.read()

    # 保留原始 4 字节签名头（本类文件签名后直接就是 op，不是 12 字节头）
    header = data[:4]

    # 从第 4 字节开始解析 op 序列
    stream = BytesIO(data[4:])
    ops = pydsc.from_stream(stream, game_hint='FT')

    # 1) 定位 MUSIC_PLAY
    music_idx = None
    for i, op in enumerate(ops):
        if op.op_name == 'MUSIC_PLAY':
            music_idx = i
            break
    if music_idx is None:
        raise Exception('未找到 MUSIC_PLAY')

    # 2) 找到 MUSIC_PLAY 之前最近的 TIME，取其值作为基准
    time_idx = None
    for j in range(music_idx - 1, -1, -1):
        if ops[j].op_name == 'TIME':
            time_idx = j
            break
    if time_idx is None:
        raise Exception('MUSIC_PLAY 之前没有 TIME')

    base_time = ops[time_idx].param_values[0]
    new_time = base_time + offset

    # 3) 该 TIME 组内的事件（不含 TIME 本身，不含边界 TIME/END）
    group_end = _group_end(ops, time_idx)
    group_events = ops[time_idx + 1 : group_end]

    if len(group_events) == 1 and group_events[0].op_name == 'MUSIC_PLAY':
        # 情况 A：MUSIC_PLAY 独占这个 TIME，直接改 TIME 值即可
        ops[time_idx].param_values[0] = new_time
        mode = '直接修改 TIME 值'
    else:
        # 情况 B：与其它事件共享 TIME
        #   移除 MUSIC_PLAY，然后在“组内最后一个事件”之后插入新 TIME，
        #   再把 MUSIC_PLAY 移到新 TIME 之后
        music_op = ops[music_idx]
        ops.pop(music_idx)

        # 移除后重新计算组边界（time_idx 不变，因为它在 music_idx 之前）
        group_end = _group_end(ops, time_idx)
        # 组内最后一个事件位于 group_end - 1，新 TIME 插在 group_end 处
        new_time_op = DscOp.from_name('FT', 'TIME', [new_time])
        ops.insert(group_end, new_time_op)
        ops.insert(group_end + 1, music_op)
        mode = '新增 TIME 并移动 MUSIC_PLAY'

    # 4) 写回：4 字节签名头 + 各 op
    out = BytesIO()
    out.write(header)
    for op in ops:
        op.write_to_stream(out)

    if output_path == '-':
        output_path = input_path

    with open(output_path, 'wb') as f:
        f.write(out.getvalue())

    return base_time, new_time, mode


def _dump_head(path, n=8):
    with open(path, 'rb') as stream:
        stream.seek(4)
        ops = pydsc.from_stream(stream, game_hint='FT')
    for op in ops[:n]:
        print('   ', op.op_name, op.param_values)


def main():
    if len(sys.argv) != 4:
        print('用法: python delay_music_play.py <input.dsc> <output.dsc> <offset>')
        print('      offset 单位为 DivaTime（1 秒 = 100000）')
        print('      output 传 "-" 表示原地覆盖 input')
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]
    offset = _parse_offset(sys.argv[3])

    base_time, new_time, mode = delay_music_play(input_path, output_path, offset)

    print('处理方式               : {}'.format(mode))
    print('MUSIC_PLAY 之前的 TIME : DivaTime({})'.format(base_time))
    print('MUSIC_PLAY 新的 TIME   : DivaTime({})'.format(new_time))
    print('已写入: {}'.format(output_path))
    print('结果开头:')
    _dump_head(output_path)


if __name__ == '__main__':
    main()
