#!/usr/bin/python3
"""生成 cover pack（config.cover_pack）的 patch_pv_db.txt 条目，并把 OGG 复制进 rom/sound/song。

用法: python cover_patch.py <pv号> <ogg文件>
  pv号: 240 或 pv_240
  ogg文件: 要复制的 OGG 文件路径

原曲信息优先取完整 DB 的 pv_NNN.another_song.0.*，
缺失时回退: name<-song_name, name_en<-song_name_en, vocal<-performer.N.chara 推断。
patch 中只写 index 0(原曲) 和 1(Cover)，length=2。
已存在的 PV 条目会被覆盖。
"""
import os
import re
import shutil
import sys

from mml import diva_db_file
from config import mod_dir, custom_skip, cover_pack

COVER_MOD = os.path.join(mod_dir, cover_pack["mod"])
PATCH_FILE = os.path.join(COVER_MOD, r"rom\patch_pv_db.txt")
SONG_DIR = os.path.join(COVER_MOD, r"rom\sound\song")

CHARA_NAME = {
    "MIK": ("初音ミク", "Miku"),
    "RIN": ("鏡音リン", "Rin"),
    "LEN": ("鏡音レン", "Len"),
    "LUK": ("巡音ルカ", "Luka"),
    "KAI": ("KAITO", "Kaito"),
    "MEI": ("MEIKO", "Meiko"),
    "GUM": ("GUMI","GUMI")
}


def normalize_pv(arg: str) -> str:
    """'240' / 'pv_240' / 'pv_0240' -> 'pv_240'"""
    m = re.fullmatch(r"(?:pv[_-]?)?0*(\d+)", arg, re.IGNORECASE)
    if not m:
        sys.exit(f"无效的PV号: {arg}")
    return "pv_%03d" % int(m.group(1))


def find_full_db(pv: str) -> tuple[str, diva_db_file | None]:
    """遍历 mod_dir/*/rom/mod_pv_db.txt，找包含 pv_NNN.song_name 的完整 DB。"""
    for d in os.listdir(mod_dir):
        if d in custom_skip:
            continue
        full = os.path.join(mod_dir, d, r"rom\mod_pv_db.txt")
        if not os.path.exists(full):
            continue
        db = diva_db_file(full)
        if pv + ".song_name" in db:
            return d, db
    return "", None


def vocal_from_chara(db: dict[str, str], pv: str) -> tuple[str, str]:
    """由 pv_NNN.performer.N.chara 推断 (vocal_disp_name, vocal_disp_name_en)。"""
    chara_keys = [k for k in db if k.startswith(pv + ".performer.") and k.endswith(".chara")]
    if not chara_keys:
        sys.exit(f"{pv} 找不到 performer.N.chara")
    num = db.get(pv + ".performer.num")
    if num is not None:
        idxs = range(int(num))
    else:
        idxs = sorted(int(k.split(".")[2]) for k in chara_keys)
    jp: list[str] = []
    en: list[str] = []
    for i in idxs:
        chara = db.get(pv + f".performer.{i}.chara")
        if chara is None:
            continue
        if chara not in CHARA_NAME:
            sys.exit(f"未知 chara: {chara} ({pv})")
        j, e = CHARA_NAME[chara]
        if j not in jp:
            jp.append(j)
            en.append(e)
    return "/".join(jp), "/".join(en)


def get_base_info(db: dict[str, str], pv: str) -> tuple[str, str, str, str]:
    """返回 (name, name_en, vocal_jp, vocal_en)。"""
    name = db.get(pv + ".another_song.0.name") or db.get(pv + ".song_name")
    if name is None:
        sys.exit(f"{pv} 在 DB 中找不到 song_name")
    name_en = db.get(pv + ".another_song.0.name_en") or db.get(pv + ".song_name_en") or ""
    vocal_jp = db.get(pv + ".another_song.0.vocal_disp_name")
    vocal_en = db.get(pv + ".another_song.0.vocal_disp_name_en")
    if vocal_jp is None or vocal_en is None:
        vj, ve = vocal_from_chara(db, pv)
        vocal_jp = vocal_jp or vj
        vocal_en = vocal_en or ve
    return name, name_en, vocal_jp, vocal_en


def build_block(pv: str, name: str, name_en: str, vocal_jp: str, vocal_en: str) -> str:
    return "\n".join([
        f"{pv}.another_song.0.name={name}",
        f"{pv}.another_song.0.name_en={name_en}",
        f"{pv}.another_song.0.vocal_disp_name={vocal_jp}",
        f"{pv}.another_song.0.vocal_disp_name_en={vocal_en}",
        f"{pv}.another_song.1.name={name}",
        f"{pv}.another_song.1.name_en={name_en}",
        f"{pv}.another_song.1.song_file_name=rom/sound/song/{pv}_{cover_pack['ogg_suffix']}.ogg",
        f"{pv}.another_song.1.vocal_disp_name={cover_pack['vocal_disp_name']}",
        f"{pv}.another_song.1.vocal_disp_name_en={cover_pack['vocal_disp_name_en']}",
        f"{pv}.another_song.length=2",
    ])


def update_patch_file(pv: str, block: str):
    """按空行拆块，删除该 PV 的旧块，把新块追加到文件末尾。"""
    if os.path.exists(PATCH_FILE):
        with open(PATCH_FILE, "r", encoding="utf_8_sig") as f:
            content = f.read()
    else:
        content = ""
    blocks = [b for b in re.split(r"\n\s*\n", content) if b.strip()]
    prefix = pv + "."
    kept = [b for b in blocks
            if not any(line.startswith(prefix) for line in b.splitlines())]
    kept.append(block)
    with open(PATCH_FILE, "w", encoding="utf_8_sig") as f:
        f.write("\n\n".join(kept) + "\n")


def copy_ogg(ogg: str, pv: str) -> str:
    os.makedirs(SONG_DIR, exist_ok=True)
    dest = os.path.join(SONG_DIR, f"{pv}_{cover_pack['ogg_suffix']}.ogg")
    shutil.copy2(ogg, dest)
    return dest


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("用法: python cover_patch.py <pv号> <ogg文件>")
    pv = normalize_pv(sys.argv[1])
    ogg = sys.argv[2]
    if not os.path.isfile(ogg):
        sys.exit(f"OGG文件不存在: {ogg}")

    mod_name, db = find_full_db(pv)
    if db is None:
        sys.exit(f"{pv} 在所有 mod_pv_db.txt 中都不存在")
    print(f"在 {mod_name} 中找到 {pv}")

    name, name_en, vocal_jp, vocal_en = get_base_info(db, pv)
    block = build_block(pv, name, name_en, vocal_jp, vocal_en)
    update_patch_file(pv, block)
    dest = copy_ogg(ogg, pv)
    print(block)
    print(f"OGG已复制: {dest}")
