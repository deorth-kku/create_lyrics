"""
OGG ↔ WebM 开头空白对齐工具。

在下载 YouTube WebM 音频后，比较其与 OGG 的开头空白差值，
若差异超过阈值，则对齐 OGG 空白并同步调整 DSC 脚本的 TIME 操作。

用法:
    from align_ogg_silence import align_ogg_silence
    align_ogg_silence(selected_mod, input_num, yt_id, config)
"""

from __future__ import annotations

import glob
import os
import shutil
import subprocess
import tempfile
import uuid
from typing import Optional

import soundfile as sf
import numpy as np

import config
from utils_ex import Aria2Rpc
from yt_dlp_to_usm import _map_remote_to_local


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SILENCE_THRESHOLD = 0.001       # 振幅阈值，低于此值视为静音
DIFF_THRESHOLD = 0.01           # 差异阈值（秒），10ms 以内视为无差异
TICKS_PER_SECOND = 100000       # DSC TIME 单位：1/100000 秒


# ---------------------------------------------------------------------------
# Silence detection
# ---------------------------------------------------------------------------

def _detect_lead_silence(audio_path: str, threshold: float = SILENCE_THRESHOLD) -> float:
    """
    检测音频文件开头的连续空白（静音）长度（秒）。
    优先 soundfile（快），不支持的格式回退 librosa（通过 ffmpeg）。
    返回空白秒数。
    """
    try:
        data, sr = sf.read(audio_path, dtype="float32")
        y = data[:, 0] if data.ndim > 1 else data
        mask = np.abs(y) > threshold
        idx = int(np.argmax(mask)) if mask.any() else len(y)
        return idx / sr
    except Exception:
        import librosa
        y, sr = librosa.load(audio_path, sr=None, mono=True)
        mask = np.abs(y) > threshold
        idx = int(np.argmax(mask)) if mask.any() else len(y)
        return idx / sr


# ---------------------------------------------------------------------------
# WebM download (audio only)
# ---------------------------------------------------------------------------

def _download_webm_audio(yt_id: str, proxy: Optional[str] = None) -> str:
    """
    通过 aria2 RPC 下载 YouTube WebM 音频，返回本地路径。
    """
    import yt_dlp

    url = f"https://youtu.be/{yt_id}"

    # 1. 解析最佳 WebM 音频 URL
    ydl_opts = {
        "format": "bestaudio[ext=webm]",
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }
    if proxy:
        ydl_opts["proxy"] = proxy
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        if info is None:
            raise RuntimeError("yt-dlp returned no info")
        video_url = info["url"]
        video_ext = info["ext"]

    # 2. 通过 aria2 RPC 下载
    rpc = Aria2Rpc(config.host, port=config.port, passwd=config.secret)
    remote_temp = config.remote_dir.rstrip("/") + "/"
    video_fn = f"{uuid.uuid4().hex}.{video_ext}"
    remote_fn = os.path.join(remote_temp, video_fn)
    task = rpc.wget(video_url, pwd=remote_temp, filename=video_fn, proxy=proxy)
    task.wait()

    # 3. 映射远程路径 → 本地路径
    local_webm = _map_remote_to_local(remote_fn)
    print(f"  WebM 音频下载完成: {local_webm}")
    return local_webm


# ---------------------------------------------------------------------------
# OGG modify
# ---------------------------------------------------------------------------

def _detect_lead_silence(audio_path: str, threshold: float = SILENCE_THRESHOLD) -> tuple[float, int]:
    """
    检测音频文件开头的连续空白（静音）长度（秒）。
    优先 soundfile（快），不支持的格式回退 librosa（通过 ffmpeg）。
    返回 (空白秒数, 采样率)。
    """
    try:
        data, sr = sf.read(audio_path, dtype="float32")
        y = data[:, 0] if data.ndim > 1 else data
        mask = np.abs(y) > threshold
        idx = int(np.argmax(mask)) if mask.any() else len(y)
        return idx / sr, sr
    except Exception:
        import librosa
        y, sr = librosa.load(audio_path, sr=None, mono=True)
        mask = np.abs(y) > threshold
        idx = int(np.argmax(mask)) if mask.any() else len(y)
        return idx / sr, sr


def _append_silence_ogg(input_path: str, output_path: str, sr: int, num_samples: int) -> None:
    """在 OGG 开头前置静音采样（PCM 拼接方案，避免 concat filter 断档）。"""
    silence_dur = num_samples / sr
    tmp_pcm = output_path + ".pcm"
    tmp_silence = output_path + ".silence.pcm"
    try:
        # 1. 原音频解码为 16bit PCM
        subprocess.run(
            ["ffmpeg", "-y", "-i", input_path,
             "-acodec", "pcm_s16le", "-ar", str(sr), "-ac", "2",
             "-f", "s16le", tmp_pcm],
            capture_output=True, check=True
        )
        # 2. 生成静音 PCM
        subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi", "-i",
             f"anullsrc=r={sr}:cl=stereo",
             "-t", str(silence_dur),
             "-acodec", "pcm_s16le", "-ar", str(sr), "-ac", "2",
             "-f", "s16le", tmp_silence],
            capture_output=True, check=True
        )
        # 3. Python 拼接 PCM
        with open(tmp_silence, "rb") as f:
            silence_data = f.read()
        with open(tmp_pcm, "rb") as f:
            audio_data = f.read()
        combined = silence_data + audio_data
        with open(tmp_pcm, "wb") as f:
            f.write(combined)
        # 4. 编码回 OGG
        subprocess.run(
            ["ffmpeg", "-y", "-f", "s16le", "-ar", str(sr), "-ac", "2",
             "-i", tmp_pcm,
             "-c:a", "libvorbis", output_path],
            capture_output=True, check=True
        )
        print(f"    写入成功：{output_path}")
    except subprocess.CalledProcessError as e:
        print(f"    ffmpeg 写入失败：{e.stderr.decode() if e.stderr else ''}")
        raise
    finally:
        for f in [tmp_pcm, tmp_silence]:
            if os.path.exists(f):
                os.remove(f)


def _trim_silence_ogg(input_path: str, output_path: str, sr: int, num_samples: int) -> None:
    """从 OGG 开头裁剪静音采样（ffmpeg 方案）。"""
    offset_sec = num_samples / sr
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", input_path,
             "-af", f"atrim=start={offset_sec}",
             "-c:a", "libvorbis", output_path],
            capture_output=True, check=True
        )
        print(f"    裁剪成功：{output_path}")
    except subprocess.CalledProcessError as e:
        print(f"    ffmpeg 裁剪失败：{e.stderr.decode() if e.stderr else ''}")
        raise


def _ogg_to_webm_ffmpeg(audio_path: str, threshold: float = SILENCE_THRESHOLD) -> float:
    """用 ffmpeg 检测 WebM 音频的开头空白（回退方案）。"""
    import subprocess
    cmd = [
        "ffprobe",
        "-i", audio_path,
        "-show_entries", "stream=codec_name",
        "-of", "csv=p=0",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    codec = result.stdout.strip()
    if codec == "opus":
        # opus 格式用 librosa 处理
        import librosa
        y, sr = librosa.load(audio_path, sr=None, mono=True)
        mask = np.abs(y) > threshold
        idx = int(np.argmax(mask)) if mask.any() else len(y)
        return idx / sr
    else:
        # 尝试 soundfile
        result = _detect_lead_silence(audio_path, threshold)
        return result[0]


from offset_times import offset_dsc_times
from config import selected_mod

# ---------------------------------------------------------------------------
# Main entry
# ---------------------------------------------------------------------------

def align_ogg_silence(input_num: int, yt_id: str) -> None:
    """
    对齐 OGG 与 WebM 音频的开头空白。

    Args:
        input_num: PV 编号（如 1891）
        yt_id: YouTube ID
    """

    ogg_path = os.path.join(selected_mod, "rom", "sound", "song", f"pv_{input_num:03d}.ogg")
    bak_path = ogg_path + ".bak"

    # 1. 检查 OGG 是否存在，不存在则直接返回
    # 2. 始终使用 bak 为源（不存在则移动 ogg→bak）
    if not os.path.exists(bak_path):
        if not os.path.exists(ogg_path):
            print(f"  OGG 不存在：{ogg_path}，跳过空白对齐")
            return
        else:
            print(f"  OGG 存在：{ogg_path}")
            shutil.move(ogg_path, bak_path)
            print(f"  原 OGG 移动为 .bak: {bak_path}")
    else:
        print(f"  检测到 .bak 文件，使用 bak 为源：{bak_path}")

    # 3. 检测 OGG 空白
    print(f"  检测 OGG 开头空白 (源：{os.path.basename(bak_path)})...")
    silence_ogg, ogg_sr = _detect_lead_silence(bak_path)
    print(f"    OGG 空白：{silence_ogg:.4f} 秒 ({silence_ogg * 1000:.1f} ms)，采样率：{ogg_sr}")

    # 3. 下载 WebM 音频
    if os.path.isabs(yt_id):
        webm_path = yt_id
    else:
        print("  下载 WebM 音频...")
        try:
            webm_path = _download_webm_audio(yt_id)
        except Exception as e:
            print(f"  WebM 下载失败: {e}，跳过空白对齐")
            return

    # 4. 检测 WebM 空白
    print("  检测 WebM 开头空白...")
    try:
        silence_webm, _ = _detect_lead_silence(webm_path)
    except Exception:
        # 回退到 ffmpeg
        silence_webm = _ogg_to_webm_ffmpeg(webm_path)
    print(f"    WebM 空白: {silence_webm:.4f} 秒 ({silence_webm * 1000:.1f} ms)")

    # 5. 计算差值
    diff = silence_webm - silence_ogg
    print(f"  差值 (WebM - OGG): {diff:.4f} 秒 ({diff * 1000:.1f} ms)")

    if abs(diff) < DIFF_THRESHOLD:
        print(f"{diff}  差异在阈值内，跳过对齐")
        shutil.move(bak_path,ogg_path)
        if yt_id!=webm_path:
            try:
                os.remove(webm_path)
                print(f"    已清理: {webm_path}")
            except OSError:
                pass
        return

    # 6. 对齐 OGG
    num_samples = int(round(abs(diff) * ogg_sr))

    if diff > 0:
        # WebM 空白更多 → OGG 需要补充空白
        print(f"  在 OGG 开头追加 {num_samples} 个静音采样 ({abs(diff) * 1000:.1f} ms)")
        _append_silence_ogg(bak_path, ogg_path, ogg_sr, num_samples)
    else:
        # WebM 空白更少 → OGG 需要裁剪空白
        print(f"  从 OGG 开头裁剪 {num_samples} 个采样 ({abs(diff) * 1000:.1f} ms)")
        _trim_silence_ogg(bak_path, ogg_path, ogg_sr, num_samples)

    # 7. 对齐 DSC
    dsc_pattern = os.path.join(selected_mod, "rom", "script", f"pv_{input_num:03d}_*.dsc")
    dsc_files = glob.glob(dsc_pattern)
    if not dsc_files:
        print(f"  未找到 DSC 文件: {dsc_pattern}")
    else:
        offset_ticks = int(round(diff * TICKS_PER_SECOND))
        for dsc_file in dsc_files:
            dsc_bak = dsc_file + ".bak"
            if os.path.exists(dsc_bak):
                # 第二次运行，.bak 已存在，直接使用
                print(f"  DSC .bak 已存在，使用 bak 为 input: {dsc_bak}")
                input_file = dsc_bak
            else:
                # 首次运行，将原文件移动为 .bak
                shutil.move(dsc_file, dsc_bak)
                input_file = dsc_bak
                print(f"  原文件移动为 .bak: {dsc_bak}")
            # 以 .bak 为 input，原文件路径为 output
            offset_dsc_times(input_file, dsc_file, offset_ticks, skip_music_start=True)

    # 8. 更新 mod_pv_db.txt 的 sabi.start_time
    sabi_key = f"pv_{input_num:03d}.sabi.start_time"
    db_path = os.path.join(selected_mod, "rom", "mod_pv_db.txt")
    if os.path.exists(db_path):
        try:
            from mml._ddf import diva_db_file
            db = diva_db_file(db_path)
            # 使用固定注释键存储原始值（包含 PV 编号）
            # 遍历所有 commit key，找到包含 pv_NNN_sabi_start_time_orig 的注释
            orig_val = None
            for key, val in db.data.items():
                if key.startswith("commit") and f"pv_{input_num:03d}_sabi_start_time_orig=" in val:
                    orig_val = float(val.split("=")[-1])
                    break

            if orig_val is None:
                # 未找到注释，从当前值读取作为原始值
                orig_val = float(db.data[sabi_key])
            new_val = orig_val + diff
            db.data[sabi_key] = str(new_val)
            db.write_file()
            print(f"  更新 {sabi_key}: {orig_val} -> {new_val} (diff={diff:.4f})")
        except Exception as e:
            print(f"  更新 sabi.start_time 失败：{e}")
    else:
        print(f"  未找到 mod_pv_db.txt: {db_path}")

    # 9. 清理 WebM
    if yt_id!=webm_path:
        try:
            os.remove(webm_path)
            print(f"  已清理 WebM: {webm_path}")
        except OSError:
            pass

    print("  空白对齐完成")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print(f"用法: python {sys.argv[0]} <input_num> <yt_id>")
        sys.exit(1)
    align_ogg_silence(int(sys.argv[1]), sys.argv[2])
