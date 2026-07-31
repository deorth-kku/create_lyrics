"""
补全脚本：将 out 中缺失的帧从 source 硬链接过来。
"""
import os
import time

SOURCE_DIR = "E:/ocr/source"
OUT_DIR = "E:/ocr/out"

def main():
    print("Scanning source and out directories...")
    source_files = set(f.replace('.png', '') for f in os.listdir(SOURCE_DIR) if f.endswith('.png'))
    out_files = set(f.replace('.png', '') for f in os.listdir(OUT_DIR) if f.endswith('.png'))
    
    missing = source_files - out_files
    print(f"Source frames: {len(source_files)}, Out frames: {len(out_files)}, Missing: {len(missing)}")
    
    if not missing:
        print("All frames present!")
        return
    
    print(f"Linking {len(missing)} missing frames...")
    t0 = time.time()
    linked = 0
    for idx in sorted(missing):
        src = os.path.join(SOURCE_DIR, f"{idx}.png")
        dst = os.path.join(OUT_DIR, f"{idx}.png")
        try:
            os.link(src, dst)
            linked += 1
        except Exception as e:
            print(f"  Error linking {idx}: {e}")
    
    print(f"Linked {linked}/{len(missing)} in {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
