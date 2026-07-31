"""
Subtitle removal script v6 - vectorized hash comparison.
- Pre-load all reference hashes and subtitle hashes
- Use vectorized hamming distance for fast comparison
"""

import json
import os
import time
import numpy as np
from PIL import Image
import imagehash

SOURCE_DIR = "E:/ocr/source"
DST_DIR = "F:/TEMP/ocr_dst"
OUT_DIR = "E:/ocr/out"

SUB_Y_CENTER_MIN = 850
SUB_Y_CENTER_MAX = 1080
SUB_WIDTH_MIN = 300
SUB_CONF_MIN = 0.8


def has_subtitle(ocr_data):
    rec_boxes = ocr_data.get("rec_boxes", [])
    rec_scores = ocr_data.get("rec_scores", [])
    for i, box in enumerate(rec_boxes):
        x1, y1, x2, y2 = box
        w = x2 - x1
        y_center = (y1 + y2) / 2.0
        conf = rec_scores[i] if i < len(rec_scores) else 0
        if w >= SUB_WIDTH_MIN and SUB_Y_CENTER_MIN <= y_center <= SUB_Y_CENTER_MAX and conf >= SUB_CONF_MIN:
            return True
    return False


def load_frames_as_array(indices, source_dir, size=128):
    """Load frames as normalized numpy arrays for comparison."""
    arrays = []
    total = len(indices)
    for i, idx in enumerate(indices):
        img_path = os.path.join(source_dir, f"{idx + 1:05d}.png")
        if os.path.exists(img_path):
            img = Image.open(img_path).convert("L").resize((size, size))
            arr = np.array(img, dtype=np.float32).ravel()
            arr = (arr - arr.mean()) / (arr.std() + 1e-6)
            arrays.append(arr)
        if (i + 1) % 500 == 0:
            print(f"    Loaded {i+1}/{total}...")
    print(f"  Done loading {len(arrays)} frames")
    return np.array(arrays)


def main():
    print("Scanning OCR results...")
    ocr_files = sorted([f for f in os.listdir(DST_DIR) if f.endswith("_res.json")])
    n = len(ocr_files)
    print(f"Total frames: {n}")

    subtitle_frames = []
    clean_frames = []

    start = time.time()
    for i, fname in enumerate(ocr_files):
        fpath = os.path.join(DST_DIR, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        if has_subtitle(data):
            subtitle_frames.append(i)
        else:
            clean_frames.append(i)
        if (i + 1) % 2000 == 0:
            print(f"  Scanned {i+1}/{n}...")
    print(f"  Classify done in {time.time()-start:.1f}s")
    print(f"  Subtitle: {len(subtitle_frames)}, Clean: {len(clean_frames)}")

    # Find clean reference segment (last 5%)
    ref_start = int(n * 0.95)
    ref_indices = [i for i in range(ref_start, n) if i in set(clean_frames)]
    if not ref_indices:
        ref_indices = clean_frames
    print(f"\nReference frames: {len(ref_indices)} (indices {ref_indices[0]}-{ref_indices[-1]})")

    # Sample 100 reference frames for speed
    if len(ref_indices) > 100:
        step = len(ref_indices) // 100
        ref_indices = ref_indices[::step][:100]
    print(f"  Using {len(ref_indices)} sampled reference frames")

    # Load reference frames
    print("\nLoading reference frames...")
    t0 = time.time()
    ref_arrays = load_frames_as_array(ref_indices, SOURCE_DIR)
    ref_norm = ref_arrays / (np.linalg.norm(ref_arrays, axis=1, keepdims=True) + 1e-6)
    print(f"  Loaded {len(ref_norm)} reference frames in {time.time()-t0:.1f}s")

    # Load all subtitle frames
    print(f"\nLoading {len(subtitle_frames)} subtitle frames...")
    t0 = time.time()
    sub_arrays = load_frames_as_array(subtitle_frames, SOURCE_DIR)
    sub_norm = sub_arrays / (np.linalg.norm(sub_arrays, axis=1, keepdims=True) + 1e-6)
    print(f"  Loaded in {time.time()-t0:.1f}s")

    # Compute cosine similarity matrix
    print("\nComputing similarities...")
    t0 = time.time()
    sim_matrix = sub_norm @ ref_norm.T  # (N, num_refs)
    print(f"  Done in {time.time()-t0:.1f}s")

    # Find best match for each subtitle frame
    print("\nFinding best matches...")
    best_local = np.argmax(sim_matrix, axis=1)
    best_sims = np.max(sim_matrix, axis=1)

    ref_indices_arr = np.array(ref_indices)
    replacements = {}
    for rank, si in enumerate(subtitle_frames):
        bi = int(ref_indices_arr[best_local[rank]].item())
        sim = float(best_sims[rank].item())
        replacements[si] = (bi, sim)

    print(f"  Avg similarity: {best_sims.mean():.4f}")
    for si, (bi, sim) in list(replacements.items())[:5]:
        print(f"    Frame {si} -> Frame {bi} (sim={sim:.4f})")
    
    # Filter: if similarity < 0.95, treat as OCR false positive, keep original frame
    SIM_THRESHOLD = 0.95
    false_positives = {si for si, (bi, sim) in replacements.items() if sim < SIM_THRESHOLD}
    print(f"\n  False positives (sim < {SIM_THRESHOLD}): {len(false_positives)}")
    for si in list(false_positives)[:5]:
        bi, sim = replacements[si]
        print(f"    Frame {si} -> Frame {bi} (sim={sim:.4f}) [kept original]")

    # Write output using hard links
    os.makedirs(OUT_DIR, exist_ok=True)
    print(f"\nWriting {len(replacements)} frames to {OUT_DIR}...")
    written = 0
    t0 = time.time()
    for si, (bi, sim) in replacements.items():
        out_path = os.path.join(OUT_DIR, f"{si + 1:05d}.png")
        if si in false_positives:
            # False positive: keep original frame
            src_path = os.path.join(SOURCE_DIR, f"{si + 1:05d}.png")
        else:
            # True positive: use matched clean frame
            src_path = os.path.join(SOURCE_DIR, f"{bi + 1:05d}.png")
        if os.path.exists(src_path):
            # Try hard link first, fallback to copy
            try:
                os.link(src_path, out_path)
            except (OSError, NotImplementedError) as e:
                # Hard link not supported (e.g., cross-drive), use copy
                print(e)
                raise e
        else:
            src_path = os.path.join(SOURCE_DIR, f"{si + 1:05d}.png")
            Image.open(src_path).save(out_path)
        written += 1
        if (written % 500 == 0):
            print(f"  Written {written}/{len(replacements)}...")
    print(f"  Write done in {time.time()-t0:.1f}s")
    print(f"\nDone! Total {written} frames written to {OUT_DIR}")


if __name__ == "__main__":
    main()
