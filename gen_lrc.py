import os
import re
import tomllib
from datetime import time

from config import mod_dir, base_dir, base_db_fallback
from extract_timing import extract_timestamps
from has_lyrics import has_lyrics


# 含平假名/片假名即视为日语
KANA_RE = re.compile(r"[\u3040-\u309F\u30A0-\u30FF]")


def is_japanese_text(path: str) -> bool:
    try:
        with open(path, encoding="utf-8") as f:
            return bool(KANA_RE.search(f.read()))
    except Exception:
        return False


def read_db_dict(path: str) -> dict[str, str]:
    """读取 mod_pv_db.txt，自动在 utf-8-sig / cp932 之间选择可用编码。"""
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "cp932"):
        try:
            text = raw.decode(enc)
        except UnicodeDecodeError:
            continue
        data: dict[str, str] = {}
        for line in text.splitlines():
            line = line.rstrip("\n")
            if line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            data[key] = value
        return data
    # 都失败时退回 utf-8 忽略错误
    text = raw.decode("utf-8", errors="ignore")
    data = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key] = value
    return data


# 输出目录：所有 pv_xxx.lrc 平铺在这里
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lrc_out")


def fmt_lrc_time(t: float) -> str:
    t = max(0.0, t)
    m = int(t // 60)
    s = t - m * 60
    return f"[{m:02d}:{s:05.2f}]"


def write_lrc(items: list[tuple[float, str]], path: str) -> bool:
    """把 [(秒, 文本)] 写成 lrc。返回是否写了有效内容。"""
    items = sorted(items, key=lambda x: x[0])
    # 过滤掉没有任何文本的空歌词
    if not any(text.strip() for _, text in items):
        return False
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for k, v in items:
            f.write(f"{fmt_lrc_time(k)}{v}\n")
    return True


def read_toml_lrc(file: str) -> list[tuple[float, str]]:
    def time_to_float(t: time) -> float:
        return t.hour * 3600 + t.minute * 60 + t.second + t.microsecond / 1_000_000

    with open(file, "rb") as f:
        data = tomllib.load(f)
    return [(time_to_float(i["time"]), i["text"]) for i in data["lyrics"]]


def read_dsc_lrc(dsc: str, db: dict[str, str], pv: int) -> list[tuple[float, str]]:
    out: list[tuple[float, str]] = []
    for k, v in extract_timestamps(dsc).items():
        k = k / 100000
        if v == 0:
            out.append((k, ""))
        else:
            out.append((k, db.get("pv_%03d.lyric.%03d" % (pv, v), "")))
    return out


def lang_score(stem: str) -> int:
    """语言优先级：无后缀 > 日语 > 英语 > 韩语 > 其它。数值越小越优先。"""
    if "_" not in stem:
        return 0
    lang = stem.split("_")[1]
    if lang == "jp":
        return 1
    if lang.startswith("en"):
        return 2
    if lang == "ko":
        return 3
    return 4


def collect_toml_all() -> dict[int, list[tuple[str, str]]]:
    """pv 号 -> [(stem, 路径)]，保留所有语言版本，交给 main 按语言优先级挑选。"""
    result: dict[int, list[tuple[str, str]]] = {}
    for mod in os.listdir(mod_dir):
        lrcdir = os.path.join(mod_dir, mod, "lyrics_eden")
        if not os.path.isdir(lrcdir):
            continue
        for fn in os.listdir(lrcdir):
            if not fn.endswith(".toml"):
                continue
            stem = fn[:-5]
            try:
                pv = int(stem.split("_")[0])
            except ValueError:
                continue
            result.setdefault(pv, []).append((stem, os.path.join(lrcdir, fn)))
    return result


def collect_dsc() -> dict[int, tuple[str, str]]:
    """pv 号 -> (dsc 路径, db 路径)。只取 extreme 谱面。"""
    result: dict[int, tuple[str, str]] = {}
    for mod in os.listdir(mod_dir):
        db_file = os.path.join(mod_dir, mod, r"rom\mod_pv_db.txt")
        scriptdir = os.path.join(mod_dir, mod, r"rom\script")
        if not os.path.isfile(db_file) or not os.path.isdir(scriptdir):
            continue
        for fn in os.listdir(scriptdir):
            m = re.match(r"pv_(\d+)_extreme\.dsc$", fn, re.IGNORECASE)
            if not m:
                continue
            pv = int(m.group(1))
            dsc_path = os.path.join(scriptdir, fn)
            # 只保留 dsc 里真正带 LYRIC 指令的谱面（歌词文本在 db 里）
            if not has_lyrics(dsc_path):
                continue
            result[pv] = (dsc_path, db_file)
    return result


def collect_base() -> dict[int, tuple[str, str]]:
    """游戏本体 dump：pv 号 -> (dsc 路径, db 路径)。

    遍历 base_dir 下所有含 script 子目录和 *_pv_db.txt 的 rom 目录，
    只取 extreme 谱面且带 LYRIC 指令的。
    """
    result: dict[int, tuple[str, str]] = {}
    for root, dirs, files in os.walk(base_dir):
        if "script" not in dirs:
            continue
        db_files = [f for f in files if f.endswith("_pv_db.txt")]
        if db_files:
            db_file = os.path.join(root, db_files[0])
        else:
            # 本体(46000) dump 缺 db，用别人 dump 的本体 db 兜底
            db_file = base_db_fallback
        scriptdir = os.path.join(root, "script")
        for fn in os.listdir(scriptdir):
            m = re.match(r"pv_(\d+)_extreme\.dsc$", fn, re.IGNORECASE)
            if not m:
                continue
            pv = int(m.group(1))
            dsc_path = os.path.join(scriptdir, fn)
            if not has_lyrics(dsc_path):
                continue
            result[pv] = (dsc_path, db_file)
    return result


def build_merged_db() -> dict[str, str]:
    """合并所有 db：本体 fallback + 本体 dump + 所有 mod。

    key 形如 pv_NNN.lyric_NNN。合并后是超集，供 dsc+db 查文本用，
    这样本体 dsc 也能从任意 mod 的 db 里拿到日语文本。
    """
    merged: dict[str, str] = {}
    if os.path.isfile(base_db_fallback):
        merged.update(read_db_dict(base_db_fallback))
    for root, dirs, files in os.walk(base_dir):
        for f in files:
            if f.endswith("_pv_db.txt"):
                merged.update(read_db_dict(os.path.join(root, f)))
    for mod in os.listdir(mod_dir):
        dbf = os.path.join(mod_dir, mod, r"rom\mod_pv_db.txt")
        if os.path.isfile(dbf):
            merged.update(read_db_dict(dbf))
    return merged


def main() -> None:
    base = collect_base()          # pv -> (dsc, db)   日语
    dsc = collect_dsc()            # pv -> (dsc, db)   日语
    toml_all = collect_toml_all()   # pv -> [(stem, path)]
    db = build_merged_db()

    # 每个 pv 的候选：(score, kind, path)。日语优先，数值越小越优先。
    cands: dict[int, list[tuple]] = {}

    def add(pv: int, score: int, kind: str, path: str):
        cands.setdefault(pv, []).append((score, kind, path))

    for pv, (dsc_path, _db_path) in base.items():
        add(pv, 0, "base", dsc_path)
    for pv, (dsc_path, _db_path) in dsc.items():
        add(pv, 1, "dsc", dsc_path)
    for pv, variants in toml_all.items():
        for stem, path in variants:
            if stem.endswith("_jp"):
                add(pv, 2, "toml", path)
            elif is_japanese_text(path):
                add(pv, 3, "toml", path)
            else:
                add(pv, 10 + lang_score(stem), "toml", path)

    os.makedirs(OUT_DIR, exist_ok=True)

    n_toml = n_dsc = n_base = n_skip = 0
    for pv in sorted(cands):
        _, kind, path = min(cands[pv], key=lambda x: x[0])
        try:
            if kind == "toml":
                items = read_toml_lrc(path)
            else:
                items = read_dsc_lrc(path, db, pv)
        except Exception as e:
            print(f"  [ERR] pv_{pv:03d} ({kind}): {e}")
            n_skip += 1
            continue

        out_path = os.path.join(OUT_DIR, f"pv_{pv:03d}.lrc")
        if write_lrc(items, out_path):
            if kind == "toml":
                n_toml += 1
            elif kind == "base":
                n_base += 1
            else:
                n_dsc += 1
        else:
            n_skip += 1

    print(f"done. base={n_base} toml={n_toml} dsc+db={n_dsc} skipped={n_skip} -> {OUT_DIR}")


if __name__ == "__main__":
    main()
