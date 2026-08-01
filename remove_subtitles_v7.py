"""
Subtitle removal script v7 - only replace subtitle region.
- For each subtitle frame, find best matching clean frame
- Only replace the OCR-detected subtitle region with the clean frame's corresponding region
- Process 50 frames for testing
"""

import cv2
import json
import os
import time
import numpy as np
from PIL import Image

SOURCE_DIR = "E:/ocr/source"
DST_DIR = "F:/TEMP/ocr_dst"
OUT_DIR = "E:/ocr/out"

SUB_Y_CENTER_MIN = 850
SUB_Y_CENTER_MAX = 1080
SUB_WIDTH_MIN = 100
SUB_CONF_MIN = 0.2
FEATHER_KERNEL = 15  #羽化核大小


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


def get_all_subtitle_boxes(ocr_data, expand=4):
    """Get all bounding boxes of subtitle text that meet criteria, with optional expansion."""
    rec_boxes = ocr_data.get("rec_boxes", [])
    rec_scores = ocr_data.get("rec_scores", [])
    boxes = []
    for i, box in enumerate(rec_boxes):
        x1, y1, x2, y2 = box
        w = x2 - x1
        y_center = (y1 + y2) / 2.0
        conf = rec_scores[i] if i < len(rec_scores) else 0
        if w >= SUB_WIDTH_MIN and SUB_Y_CENTER_MIN <= y_center <= SUB_Y_CENTER_MAX and conf >= SUB_CONF_MIN:
            # Expand box by `expand` pixels in all directions
            x1 = max(0, x1 - expand)
            y1 = max(0, y1 - expand)
            x2 = x2 + expand
            y2 = y2 + expand
            boxes.append((x1, y1, x2, y2))
    return boxes


def create_ocr_mask(ocr_data, height, width):
    """Create binary mask from OCR boxes (255 for subtitle, 0 for background)."""
    mask = np.zeros((height, width), dtype=np.uint8)
    boxes = get_all_subtitle_boxes(ocr_data)
    for box in boxes:
        x1, y1, x2, y2 = box
        cv2.rectangle(mask, (x1, y1), (x2, y2), 255, -1)
    return mask


def poisson_blend(sub_img, ref_img, mask, kernel_size=FEATHER_KERNEL):
    """Poisson seamless cloning for better edge blending."""
    sub_img = cv2.cvtColor(np.array(sub_img), cv2.COLOR_RGB2BGR)
    ref_img = cv2.cvtColor(np.array(ref_img), cv2.COLOR_RGB2BGR)
    
    # Ensure same size
    if sub_img.shape != ref_img.shape:
        ref_img = cv2.resize(ref_img, (sub_img.shape[1], sub_img.shape[0]))
    
    # Color matching: adjust ref_img brightness to match sub_img
    src_lab = cv2.cvtColor(sub_img, cv2.COLOR_BGR2LAB).astype(np.float32)
    ref_lab = cv2.cvtColor(ref_img, cv2.COLOR_BGR2LAB).astype(np.float32)
    
    matched_lab = np.zeros_like(ref_lab)
    for i in range(3):
        src_vals = src_lab[:, :, i].ravel()
        ref_vals = ref_lab[:, :, i].ravel()
        
        src_mean = np.mean(src_vals)
        src_std = np.std(src_vals) + 1e-5
        ref_mean = np.mean(ref_vals)
        ref_std = np.std(ref_vals) + 1e-5
        
        matched_lab[:, :, i] = (ref_lab[:, :, i] - ref_mean) * (src_std / ref_std) + src_mean
    
    matched_bgr = np.clip(matched_lab, 0, 255).astype(np.uint8)
    matched_bgr = cv2.cvtColor(matched_bgr, cv2.COLOR_LAB2BGR)
    
    # Poisson seamless clone
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        x, y, w, h = cv2.boundingRect(np.vstack(contours))
        center = (x + w // 2, y + h // 2)
        result = cv2.seamlessClone(
            matched_bgr, 
            sub_img, 
            mask, 
            center, 
            cv2.NORMAL_CLONE
        )
    else:
        # Fallback to feathered blend
        blurred_mask = cv2.GaussianBlur(mask.astype(np.float32) / 255.0, (kernel_size, kernel_size), 0)
        blurred_mask = np.expand_dims(blurred_mask, axis=-1)
        result = (matched_bgr.astype(np.float32) * blurred_mask + 
                  sub_img.astype(np.float32) * (1.0 - blurred_mask))
        result = np.clip(result, 0, 255).astype(np.uint8)
    
    return cv2.cvtColor(result, cv2.COLOR_BGR2RGB)


def get_subtitle_box(ocr_data):
    """Get the bounding box of the subtitle text."""
    rec_boxes = ocr_data.get("rec_boxes", [])
    rec_scores = ocr_data.get("rec_scores", [])
    best_box = None
    best_conf = 0
    for i, box in enumerate(rec_boxes):
        x1, y1, x2, y2 = box
        w = x2 - x1
        y_center = (y1 + y2) / 2.0
        conf = rec_scores[i] if i < len(rec_scores) else 0
        if w >= SUB_WIDTH_MIN and SUB_Y_CENTER_MIN <= y_center <= SUB_Y_CENTER_MAX and conf >= SUB_CONF_MIN:
            if conf > best_conf:
                best_conf = conf
                best_box = box
    return best_box

BATCH_SIZE = 100

def load_frames_as_array(indices, source_dir):
    """Load frames as normalized numpy arrays for comparison (color)."""
    arrays = []
    total = len(indices)
    for i, idx in enumerate(indices):
        img_path = os.path.join(source_dir, f"{idx + 1:05d}.png")
        if os.path.exists(img_path):
            img = Image.open(img_path).convert("RGB")
            arr = np.array(img, dtype=np.float32).ravel()
            arr = (arr - arr.mean()) / (arr.std() + 1e-6)
            arrays.append(arr)
        if (i + 1) % BATCH_SIZE == 0:
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

    # 跳过已处理帧（输出文件已存在）
    already_done = set()
    for f in os.listdir(OUT_DIR):
        if f.endswith(".png"):
            num = int(f.replace(".png", ""))
            already_done.add(num - 1)  # 存储为 0-based index
    if already_done:
        subtitle_frames = [f for f in subtitle_frames if f not in already_done]
        print(f"  Skip {len(already_done)} already processed frames, remaining: {len(subtitle_frames)}")

    # 全量处理，分批执行

    total_batches = (len(subtitle_frames) + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"\n  全量处理 {len(subtitle_frames)} 帧，分 {total_batches} 批，每批 {BATCH_SIZE} 帧")

    # Use continuous reference frames starting from 9272
    REF_START = 9272
    SAMPLE_SIZE = 100
    ref_indices = [i for i in range(REF_START, REF_START + SAMPLE_SIZE) if i in set(clean_frames)]
    if not ref_indices:
        ref_indices = clean_frames[:SAMPLE_SIZE]
    print(f"\nReference frames: {len(ref_indices)} (continuous range {ref_indices[0]}-{ref_indices[-1]})")

    # Load reference frames once
    print("\nLoading reference frames...")
    t0 = time.time()
    ref_arrays = load_frames_as_array(ref_indices, SOURCE_DIR)
    ref_norm = ref_arrays / (np.linalg.norm(ref_arrays, axis=1, keepdims=True) + 1e-6)
    print(f"  Loaded {len(ref_norm)} reference frames in {time.time()-t0:.1f}s")

    # Process in batches
    for batch_idx in range(total_batches):
        start_idx = batch_idx * BATCH_SIZE
        end_idx = min(start_idx + BATCH_SIZE, len(subtitle_frames))
        batch_frames = subtitle_frames[start_idx:end_idx]
        
        print(f"\n--- Batch {batch_idx + 1}/{total_batches} (frames {start_idx + 1}-{end_idx}) ---")
        
        # Load current batch of subtitle frames
        print(f"Loading {len(batch_frames)} subtitle frames...")
        t0 = time.time()
        sub_arrays = load_frames_as_array(batch_frames, SOURCE_DIR)
        sub_norm = sub_arrays / (np.linalg.norm(sub_arrays, axis=1, keepdims=True) + 1e-6)
        print(f"  Loaded in {time.time()-t0:.1f}s")

        # Compute cosine similarity matrix
        print("Computing similarities...")
        t0 = time.time()
        sim_matrix = sub_norm @ ref_norm.T  # (N, num_refs)
        print(f"  Done in {time.time()-t0:.1f}s")

        # Find best match for each subtitle frame
        print("Finding best matches...")
        best_local = np.argmax(sim_matrix, axis=1)
        best_sims = np.max(sim_matrix, axis=1)

        ref_indices_arr = np.array(ref_indices)
        replacements = {}
        for rank, si in enumerate(batch_frames):
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

        # Write output for current batch
        os.makedirs(OUT_DIR, exist_ok=True)
        print(f"\nWriting {len(replacements)} frames to {OUT_DIR}...")
        written = 0
        t0 = time.time()
        for si, (bi, sim) in replacements.items():
            out_path = os.path.join(OUT_DIR, f"{si + 1:05d}.png")
            if os.path.exists(out_path):
                continue  # 已存在则跳过
            src_path = os.path.join(SOURCE_DIR, f"{si + 1:05d}.png")
            ref_path = os.path.join(SOURCE_DIR, f"{bi + 1:05d}.png")
            
            if si in false_positives:
                # False positive: keep original frame
                img = Image.open(src_path).copy()
            else:
                # True positive: replace subtitle region with matched clean frame's region
                sub_img = Image.open(src_path).convert("RGB")
                ref_img = Image.open(ref_path).convert("RGB")
                
                # Get all subtitle boxes from OCR data
                sub_ocr_path = os.path.join(DST_DIR, f"{si + 1:05d}_res.json")
                with open(sub_ocr_path, "r", encoding="utf-8") as f:
                    sub_ocr = json.load(f)
                all_boxes = get_all_subtitle_boxes(sub_ocr)
                
                if all_boxes:
                    # Poisson blend the entire subtitle region
                    sub_np = np.array(sub_img)
                    full_mask = np.zeros(sub_np.shape[:2], dtype=np.uint8)
                    for box in all_boxes:
                        x1, y1, x2, y2 = box
                        cv2.rectangle(full_mask, (x1, y1), (x2, y2), 255, -1)
                    
                    blended = poisson_blend(sub_np, ref_img, full_mask)
                    sub_img = Image.fromarray(blended)
                else:
                    # No subtitle boxes found, keep original
                    pass
                
                img = sub_img.convert("RGB")
            
            img.save(out_path)
            written += 1
            if (written % BATCH_SIZE == 0):
                print(f"  Written {written}/{len(replacements)}...")
        print(f"  Batch {batch_idx + 1} write done in {time.time()-t0:.1f}s")
        print(f"  Processed {end_idx - start_idx} frames in batch {batch_idx + 1}/{total_batches}")
    
    print(f"\nDone! Total frames processed.")


if __name__ == "__main__":
    main()
