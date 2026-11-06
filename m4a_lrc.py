import os
import shutil
import sys

from mutagen.mp4 import MP4
from config import MUSIC_DIR
from gen_lrc import OUT_DIR, build_merged_db




def build_title_map() -> dict[str, int]:
    """歌名 -> pv 号。

    来自合并 db：
      pv_NNN.song_name             主歌
      pv_NNN.another_song.M.name   cover/副歌
    """
    db = build_merged_db()
    m: dict[str, int] = {}
    for k, v in db.items():
        if k.endswith(".song_name") or (
            ".another_song." in k and k.endswith(".name")
        ):
            pv = int(k.split(".")[0][3:])
            m[v] = pv
    return m


def get_title(path: str) -> str | None:
    tags = MP4(path).tags
    if tags is None:
        return None
    vals = tags.get("\u00a9nam")  # ©nam
    return vals[0] if vals else None


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    title_map = build_title_map()

    m4as = []
    for root, _dirs, files in os.walk(MUSIC_DIR):
        for f in files:
            if f.lower().endswith(".m4a"):
                m4as.append(os.path.join(root, f))

    matched = 0
    trimmed = 0
    no_title: list[str] = []
    no_pv: list[tuple[str, str]] = []
    no_lrc: list[tuple[str, int]] = []

    for path in sorted(m4as):
        title = get_title(path)
        if title is None:
            no_title.append(path)
            continue
        pv = title_map.get(title)
        if pv is None and title.endswith(" Ver)"):
            # 结尾是 (… Ver)，trim 掉再匹配一次
            idx = title.rfind(" (")
            if idx > 0:
                pv = title_map.get(title[:idx])
                if pv is not None:
                    trimmed += 1
        if pv is None:
            no_pv.append((path, title))
            continue
        lrc = os.path.join(OUT_DIR, f"pv_{pv:03d}.lrc")
        if not os.path.isfile(lrc):
            no_lrc.append((path, pv))
            continue
        dst = os.path.splitext(path)[0] + ".lrc"
        shutil.copyfile(lrc, dst)
        matched += 1

    report = os.path.join(os.path.dirname(os.path.abspath(__file__)), "m4a_lrc_report.txt")
    with open(report, "w", encoding="utf-8") as f:
        f.write(f"total={len(m4as)} matched={matched} (trim={trimmed})\n")
        f.write(f"no_title={len(no_title)} no_pv={len(no_pv)} no_lrc={len(no_lrc)}\n\n")
        f.write(f"=== NO_PV ({len(no_pv)}) ===\n")
        for p, t in no_pv:
            f.write(f"{t}\t<- {p}\n")
        f.write(f"\n=== NO_LRC ({len(no_lrc)}) ===\n")
        for p, pv in no_lrc:
            f.write(f"pv_{pv:03d}\t<- {p}\n")
        f.write(f"\n=== NO_TITLE ({len(no_title)}) ===\n")
        for p in no_title:
            f.write(f"{p}\n")

    print(f"total={len(m4as)} matched={matched} (trim={trimmed})")
    print(f"no_title={len(no_title)} no_pv={len(no_pv)} no_lrc={len(no_lrc)}")
    print(f"report -> {report}")


if __name__ == "__main__":
    main()
