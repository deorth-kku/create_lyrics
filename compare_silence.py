"""
比较两个音频文件开头空白（静音）长度的脚本。

用法:
    python compare_silence.py audio1.wav audio2.wav

输出:
    每个文件的开头空白时长，以及两者的差值。
"""

import sys
import warnings
import numpy as np
import soundfile as sf
import librosa

# 抑制 librosa / soundfile / audioread 的警告
warnings.filterwarnings("ignore")

DEFAULT_THRESHOLD = 0.001  # 振幅阈值，低于此值视为静音


def _load_with_soundfile(audio_path: str, threshold: float) -> tuple[float, float]:
    """用 soundfile 快速读取（支持 WAV/OGG/FLAC/AIFF 等），返回 (采样率, 空白秒数)"""
    data, sr = sf.read(audio_path, dtype="float32")
    y = data[:, 0] if data.ndim > 1 else data  # 立体声取左声道

    mask = np.abs(y) > threshold
    idx = np.argmax(mask) if mask.any() else len(y)
    return sr, idx / sr


def _load_with_librosa(audio_path: str, threshold: float) -> tuple[float, float]:
    """用 librosa 读取（支持 WebM/MP3 等，通过 ffmpeg），返回 (采样率, 空白秒数)"""
    y, sr = librosa.load(audio_path, sr=None, mono=True)
    mask = np.abs(y) > threshold
    idx = np.argmax(mask) if mask.any() else len(y)
    return sr, idx / sr


def find_lead_silence(audio_path: str, threshold: float = DEFAULT_THRESHOLD) -> tuple[float, str]:
    """
    检测音频文件开头的连续空白（静音）长度（秒）。
    优先 soundfile（快），不支持的格式回退 librosa（通过 ffmpeg）。
    返回 (空白秒数, 使用的后端名称)
    """
    try:
        sr, silence = _load_with_soundfile(audio_path, threshold)
        return silence, "soundfile"
    except Exception:
        sr, silence = _load_with_librosa(audio_path, threshold)
        return silence, "librosa"


def main():
    if len(sys.argv) != 3:
        print(f"用法: python {sys.argv[0]} <audio_file_1> <audio_file_2>")
        print("示例: python compare_silence.py song1.wav song2.wav")
        sys.exit(1)

    file1, file2 = sys.argv[1], sys.argv[2]

    print(f"正在分析: {file1}")
    silence1, backend1 = find_lead_silence(file1)
    print(f"  开头空白时长: {silence1:.4f} 秒 ({silence1 * 1000:.1f} ms) [{backend1}]")

    print(f"正在分析: {file2}")
    silence2, backend2 = find_lead_silence(file2)
    print(f"  开头空白时长: {silence2:.4f} 秒 ({silence2 * 1000:.1f} ms) [{backend2}]")

    diff = silence2 - silence1
    print(f"\n差值 (file2 - file1): {diff:.4f} 秒 ({diff * 1000:.1f} ms)")

    if diff > 0:
        print(f"  file2 比 file1 多 {abs(diff) * 1000:.1f} ms 的开头空白")
    elif diff < 0:
        print(f"  file1 比 file2 多 {abs(diff) * 1000:.1f} ms 的开头空白")
    else:
        print("  两者的开头空白时长相同")


if __name__ == "__main__":
    main()
