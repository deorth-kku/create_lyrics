"""
delay_music_play.py 的反操作：不移动 MUSIC_PLAY，而是把电影事件往后移。

背景：
    原始文件开头通常是：
        TIME [DivaTime(0)]
        CHANGE_FIELD [1]
        MUSIC_PLAY []
        MOVIE_PLAY [True]
        MOVIE_DISP [1]
        TIME [DivaTime(338600)]
        ...

    MUSIC_PLAY / MOVIE_PLAY / MOVIE_DISP 共享同一个 TIME(0)。
    本脚本把电影事件移到“原 TIME 值 + OFFSET”的新 TIME 上，MUSIC_PLAY 保持原位。
    （不确定 MOVIE_DISP 发生前会不会先显示一个默认 3D 图形，所以提供只移动
      MOVIE_PLAY 的模式。）

两种模式：

  默认（移动 MOVIE_PLAY + MOVIE_DISP）：
        TIME [DivaTime(0)]
        CHANGE_FIELD [1]
        MUSIC_PLAY []
        TIME [DivaTime(OFFSET)]
        MOVIE_PLAY [True]
        MOVIE_DISP [1]
        TIME [DivaTime(338600)]

  只移动 MOVIE_PLAY（MOVIE_DISP 保持原位）：
        TIME [DivaTime(0)]
        CHANGE_FIELD [1]
        MUSIC_PLAY []
        MOVIE_DISP [1]
        TIME [DivaTime(OFFSET)]
        MOVIE_PLAY [True]
        TIME [DivaTime(338600)]

新 TIME 会插在“留在原组里的最后一个事件”之后，被移动的事件按原相对顺序跟在新 TIME 后面。

用法：
    python move_movie.py <input.dsc> <output.dsc> <offset> [--play-only]

    - offset 单位是 DivaTime（1 秒 = 100000）。
    - output 传 "-" 表示原地覆盖 input。
    - --play-only：只移动 MOVIE_PLAY，MOVIE_DISP 保持原位。
"""

import argparse
from io import BytesIO

from pydiva import pydsc
from pydiva.pydsc import DscOp
from delay_music_play import _group_end, _parse_offset


def move_movie(input_path, output_path, offset, play_only=False):
    with open(input_path, 'rb') as f:
        data = f.read()

    # 保留原始 4 字节签名头（本类文件签名后直接就是 op，不是 12 字节头）
    header = data[:4]

    # 从第 4 字节开始解析 op 序列
    stream = BytesIO(data[4:])
    ops = pydsc.from_stream(stream, game_hint='FT')

    # 1) 定位 MOVIE_PLAY
    movie_play_idx = None
    for i, op in enumerate(ops):
        if op.op_name == 'MOVIE_PLAY':
            movie_play_idx = i
            break
    if movie_play_idx is None:
        raise Exception('未找到 MOVIE_PLAY')

    # 2) 找到 MOVIE_PLAY 之前最近的 TIME，取其值作为基准
    time_idx = None
    for j in range(movie_play_idx - 1, -1, -1):
        if ops[j].op_name == 'TIME':
            time_idx = j
            break
    if time_idx is None:
        raise Exception('MOVIE_PLAY 之前没有 TIME')

    base_time = ops[time_idx].param_values[0]
    new_time = base_time + offset

    # 3) 该 TIME 组的边界
    group_end = _group_end(ops, time_idx)

    # 4) 确定要移动的事件（按组内出现顺序）
    wanted = ['MOVIE_PLAY'] if play_only else ['MOVIE_PLAY', 'MOVIE_DISP']
    moving_indices = [i for i in range(time_idx + 1, group_end) if ops[i].op_name in wanted]

    if movie_play_idx not in moving_indices:
        raise Exception('MOVIE_PLAY 不在其 TIME 组内?')
    if not play_only and not any(ops[i].op_name == 'MOVIE_DISP' for i in moving_indices):
        raise Exception('MOVIE_DISP 不在 MOVIE_PLAY 的同一 TIME 组内')

    moving_ops = [ops[i] for i in moving_indices]

    # 5) 从组里移除要移动的事件（从后往前删，保持索引有效）
    for i in sorted(moving_indices, reverse=True):
        ops.pop(i)

    # 6) 重新计算组边界，把新 TIME 插在“留在原组的最后一个事件”之后
    group_end = _group_end(ops, time_idx)
    new_time_op = DscOp.from_name('FT', 'TIME', [new_time])
    ops.insert(group_end, new_time_op)

    # 7) 把被移动的事件按原相对顺序插到新 TIME 之后
    for k, mop in enumerate(moving_ops):
        ops.insert(group_end + 1 + k, mop)

    # 8) 写回：4 字节签名头 + 各 op
    out = BytesIO()
    out.write(header)
    for op in ops:
        op.write_to_stream(out)

    if output_path == '-':
        output_path = input_path

    with open(output_path, 'wb') as f:
        f.write(out.getvalue())

    return base_time, new_time, len(moving_ops)


def _dump_head(path, n=8):
    with open(path, 'rb') as stream:
        stream.seek(4)
        ops = pydsc.from_stream(stream, game_hint='FT')
    for op in ops[:n]:
        print('   ', op.op_name, op.param_values)


def main():
    parser = argparse.ArgumentParser(
        description='把 DSC 里的电影事件(MOVIE_PLAY/MOVIE_DISP)移到更晚的 TIME，MUSIC_PLAY 保持原位。')
    parser.add_argument('input', help='输入 DSC 文件')
    parser.add_argument('output', help='输出 DSC 文件，传 "-" 表示原地覆盖 input')
    parser.add_argument('offset', help='偏移量，单位 DivaTime（1 秒 = 100000）')
    parser.add_argument('--play-only', action='store_true',
                        help='只移动 MOVIE_PLAY，MOVIE_DISP 保持原位')
    args = parser.parse_args()

    offset = _parse_offset(args.offset)

    base_time, new_time, moved_cnt = move_movie(args.input, args.output, offset, args.play_only)

    mode = '只移动 MOVIE_PLAY' if args.play_only else '移动 MOVIE_PLAY + MOVIE_DISP'
    print('处理方式               : {}'.format(mode))
    print('MOVIE_PLAY 之前的 TIME : DivaTime({})'.format(base_time))
    print('新建的 TIME            : DivaTime({})'.format(new_time))
    print('移动的事件数           : {}'.format(moved_cnt))
    print('已写入: {}'.format(args.output))
    print('结果开头:')
    _dump_head(args.output)


if __name__ == '__main__':
    main()
