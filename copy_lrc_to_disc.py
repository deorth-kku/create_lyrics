#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
从游戏原盘 CD 的 mp3 文件名提取标题，用 search_song 找到对应 pv 号，
把 lrc_out/pv_XXX.lrc 复制到 mp3 旁边，命名为 <mp3同名>.lrc。

用法:
    python copy_lrc_to_disc.py            # dry-run，只打印映射
    python copy_lrc_to_disc.py --copy     # 实际复制
"""
import os
import sys
import shutil
from collections.abc import Generator

from mml import diva_db_file
from config import mod_dir, custom_skip

DISC = r'Z:\music\[160608]初音ミク -Project DIVA- X Complete Collection(完全生産限定盤)(Blu-ray Disc付)[320K]'
LRC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lrc_out')

# 需要从标题里去掉的片段
STRIP_MARKS = ['〔Game Version〕', '[Game Version]', '(Game Version)']

# 标点归一化：文件名与游戏 db 里同一首歌的标点写法不同
PUNCT_MAP = str.maketrans({
    '・': '.', '～': '~', '＊': 'x', '〜': '~',
    '－': '-', '—': '-', '–': '-',
})


def normalize(s: str) -> str:
    """归一化标点并去掉所有空格，便于模糊匹配。"""
    return s.translate(PUNCT_MAP).replace(' ', '').replace('\u3000', '')


def extract_title(filename: str) -> str:
    """从 mp3 文件名提取标题（去掉扩展名和 Game Version 标记）。"""
    title = os.path.splitext(filename)[0]
    for mark in STRIP_MARKS:
        title = title.replace(mark, '')
    return title.strip()


def iter_db():
    """遍历所有 mod 的 song_name，yield (pvid, song_name)。"""
    for d in os.listdir(mod_dir):
        if d in custom_skip:
            continue
        full = os.path.join(mod_dir, d, r'rom\mod_pv_db.txt')
        if os.path.exists(full):
            db = diva_db_file(full)
            db.readlines()
            for k, v in db.items():
                if k.endswith('song_name'):
                    yield k.split('.')[0], v


def find_pv(title: str) -> Generator[tuple[str, str]]:
    """按归一化后的标题在 db 里做子串匹配，yield (pvid, song_name)。"""
    q = normalize(title)
    for pvid, name in iter_db():
        if q in normalize(name):
            yield pvid, name


def collect_mp3s(disc: str):
    for root, _dirs, files in os.walk(disc):
        for f in files:
            if f.lower().endswith('.mp3'):
                yield os.path.join(root, f)


def main():
    do_copy = '--copy' in sys.argv

    results = []
    for mp3 in sorted(collect_mp3s(DISC)):
        title = extract_title(os.path.basename(mp3))
        matches = list(find_pv(title))
        if not matches:
            results.append((mp3, title, None, None))
            continue
        # 取第一个匹配
        pvid, name = matches[0]
        results.append((mp3, title, pvid, name))

    # 打印映射
    for mp3, title, pvid, name in results:
        if pvid is None:
            print(f'[NO MATCH] {title!r}')
        else:
            lrc = os.path.join(LRC_DIR, pvid + '.lrc')
            exists = 'OK ' if os.path.exists(lrc) else 'MISSING-LRC'
            dst = os.path.splitext(mp3)[0] + '.lrc'
            print(f'[{exists}] {title!r} -> {pvid}  ({name!r})')
            print(f'          src: {lrc}')
            print(f'          dst: {dst}')

    # 统计
    matched = sum(1 for r in results if r[2] is not None)
    print(f'\n共 {len(results)} 个 mp3，匹配到 {matched} 个')

    if do_copy:
        copied = 0
        for mp3, title, pvid, name in results:
            if pvid is None:
                continue
            lrc = os.path.join(LRC_DIR, pvid + '.lrc')
            if not os.path.exists(lrc):
                print(f'[SKIP-NO-LRC] {title!r} -> {pvid}')
                continue
            dst = os.path.splitext(mp3)[0] + '.lrc'
            shutil.copyfile(lrc, dst)
            copied += 1
            print(f'[COPIED] {os.path.basename(dst)}')
        print(f'\n已复制 {copied} 个 lrc')


if __name__ == '__main__':
    main()
