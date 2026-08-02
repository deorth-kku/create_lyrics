"""
yt-dlp to USM CLI

A standalone command-line tool that downloads a YouTube video (native VP9),
remuxes it to IVF, and converts it to a Criware USM file using the Wannacri
library.

Usage:
    Assets/Python/python.exe yt-dlp_to_usm.py "https://www.youtube.com/watch?v=..." [-o output.usm] [--key 0x...]

Prerequisites:
    yt-dlp must be installed into the bundled Python interpreter:
        Assets/Python/python.exe -m pip install -U yt-dlp
"""

from __future__ import annotations

import argparse
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
from typing import Optional, Tuple

import yt_dlp
from utils_ex import Aria2Rpc


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
DEFAULT_FFMPEG_DIR = SCRIPT_DIR / "Assets" / "FFmpeg"
DEFAULT_ENCODING = "shift-jis"
DEFAULT_QUALITY = "bestvideo[ext=webm][vcodec=vp9]"
DEFAULT_SUFFIX = ".ivf"
VIDEO_CODEC = "vp9"
MPEG_CODEC = 9  # VP9 in USM


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

import config  # guaranteed to exist


def _map_remote_to_local(remote_path: str) -> str:
    rd = config.remote_dir.rstrip("/")
    ld = config.local_dir.rstrip("/")
    if remote_path.startswith(rd):
        return ld + remote_path[len(rd):]
    return remote_path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def resolve_ffmpeg_paths() -> Tuple[str, str]:
    """Resolve absolute paths for ffmpeg.exe and ffprobe.exe from PATH."""
    import shutil
    for name in ("ffmpeg", "ffprobe"):
        exe = shutil.which(name)
        if exe is None:
            print(f"ERROR: {name} not found in PATH")
            sys.exit(1)
    return shutil.which("ffmpeg"), shutil.which("ffprobe")


def remux_webm_to_ivf(webm_path: str, ffmpeg_exe: str, ivf_path: str) -> None:
    """Remux a .webm file to raw .ivf using FFmpeg (bitstream copy)."""
    cmd = [
        ffmpeg_exe,
        "-y",
        "-i", webm_path,
        "-c", "copy",
        "-f", "ivf",
        ivf_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR: FFmpeg remux failed (exit {result.returncode}):")
        print(result.stderr)
        sys.exit(1)

import uuid
def download_youtube_video(
    url: str,
    ffmpeg_exe: str,
    output_dir: pathlib.Path,
    quality: str = DEFAULT_QUALITY,
    proxy: Optional[str] = None,
) -> str:
    """
    Use yt-dlp only to resolve the best VP9 video URL, then download it
    via aria2 RPC (remote_dir on the aria2 host, mapped to local_dir).
    Returns the local path to the downloaded .webm file.
    """
    # 1. Resolve the best VP9 webm URL with yt-dlp (no download)
    ydl_opts = {
        "format": quality,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }
    if proxy:
        ydl_opts["proxy"] = proxy
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        if info is None:
            print("ERROR: yt-dlp returned no info.")
            sys.exit(1)
        video_url = info["url"]
        video_ext = info["ext"]

    # 2. Download via aria2 RPC
    rpc = Aria2Rpc(config.host, port=config.port, passwd=config.secret)
    remote_temp = config.remote_dir.rstrip("/") + "/"
    video_fn = f"{uuid.uuid4().hex}.{video_ext}"
    remote_fn = os.path.join(remote_temp, video_fn)
    task = rpc.wget(video_url, pwd=remote_temp, filename=video_fn, proxy=proxy)
    task.wait()

    # 3. Map remote path -> local path
    local_webm = _map_remote_to_local(remote_fn)
    print(f"  Downloaded: {local_webm}")
    return local_webm


def _progress_hook(d: dict) -> None:
    """Console progress hook for yt-dlp."""
    status = d.get("status")
    if status == "downloading":
        pct = d.get("_percent_str", "?").strip()
        speed = d.get("_speed_str", "?").strip()
        eta = d.get("_eta_str", "?").strip()
        print(f"\r  Downloading... {pct}  Speed: {speed}  ETA: {eta}", end="", flush=True)
    elif status == "finished":
        print(f"\n  Download finished.")


def _safe_filename(title: str) -> str:
    """Sanitise a string for use as a filename."""
    bad = r'<>:"/\|?*'
    out = title
    for ch in bad:
        out = out.replace(ch, "_")
    return out.strip() or "output"


# ---------------------------------------------------------------------------
# Wannacri conversion
# ---------------------------------------------------------------------------

def convert_to_usm(
    ivf_path: str,
    ffprobe_exe: str,
    output_path: pathlib.Path,
    key: Optional[int],
    encoding: str = DEFAULT_ENCODING,
) -> None:
    """
    Build a USM from *ivf_path* using Wannacri and write it to *output_path*.
    """
    # Import here so the user can use the script without installing wannacri
    # if they only need yt-dlp.
    from wannacri.codec import Sofdec2Codec
    from wannacri.usm import Usm, Vp9, OpMode

    # 1. Probe & verify codec
    codec = Sofdec2Codec.from_file(ivf_path, ffprobe_path=ffprobe_exe)
    if codec is not Sofdec2Codec.VP9:
        print(f"ERROR: Expected VP9/IVF but got {codec}.")
        sys.exit(1)

    # 2. Build the Vp9 container
    video = Vp9(ivf_path, ffprobe_path=ffprobe_exe)

    # 3. Wrap in a Usm
    usm = Usm(videos=[video], audios=None, key=key, version=16777984)

    # 4. Pick the operation mode
    mode = OpMode.NONE if key is None else OpMode.ENCRYPT

    # 5. Stream packets to disk
    with open(output_path, "wb") as f:
        for packet in usm.stream(mode, encoding=encoding):
            f.write(packet)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def yt_dlp_to_usm(
    url: str,
    output: Optional[str] = None,
    key: Optional[str] = None,
    encoding: str = DEFAULT_ENCODING,
    quality: str = DEFAULT_QUALITY,
    keep_intermediate: bool = False,
    no_cleanup: bool = False,
) -> str:
    """
    Download a YouTube video (native VP9) and convert it to a USM file.

    This is a convenient wrapper around the CLI entry point for programmatic use.

    Args:
        url: YouTube video URL.
        output: Output .usm file path. Defaults to ``<title>.usm`` in cwd.
        key: Hex or decimal encryption key (e.g. ``"0x1234abcd"``). ``None`` for unencrypted.
        encoding: Character encoding for the USM (default: ``shift-jis``).
        quality: yt-dlp format selector (default: ``bestvideo[ext=webm][vcodec=vp9]``).
        keep_intermediate: Keep downloaded .webm / .ivf files after conversion.
        no_cleanup: Disable automatic cleanup of the temp download directory.

    Returns:
        The path to the output .usm file.
    """
    ffmpeg_exe, ffprobe_exe = resolve_ffmpeg_paths()

    # Parse the key argument (hex or decimal)
    parsed_key: Optional[int] = None
    if key is not None:
        parsed_key = int(key, 0)  # auto-detect hex (0x...) vs decimal

    print(f"  aria2 host: {config.host}:{config.port}, "
          f"remote_dir: {config.remote_dir}, local_dir: {config.local_dir}")

    temp_dir = pathlib.Path(tempfile.mkdtemp(prefix="wannacri_yt_"))
    print(f"Working directory: {temp_dir}")

    try:
        # --- Step 1: Download via aria2 RPC ---
        print(f"Downloading YouTube video (format: {quality})...")
        webm_path = download_youtube_video(url, ffmpeg_exe, temp_dir, quality)

        # --- Step 2: Remux to IVF ---
        ivf_path = str(temp_dir / "video.ivf")
        print("Remuxing .webm -> .ivf (bitstream copy)...")
        remux_webm_to_ivf(webm_path, ffmpeg_exe, ivf_path)
        print(f"  IVF written: {ivf_path}")

        # --- Step 3: Convert to USM ---
        if output:
            output_path = pathlib.Path(output)
        else:
            safe = _safe_filename("youtube_video")
            output_path = pathlib.Path.cwd() / f"{safe}.usm"

        print(f"Converting to USM (output: {output_path})...")
        convert_to_usm(ivf_path, ffprobe_exe, output_path, parsed_key, encoding)
        print(f"Done. USM written to: {output_path}")
        return str(output_path)

    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise

    finally:
        if not no_cleanup:
            try:
                shutil.rmtree(temp_dir)
                if not keep_intermediate:
                    print(f"Cleaned up: {temp_dir}")
                else:
                    print(f"Kept intermediates in: {temp_dir}")
            except OSError:
                pass


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download a YouTube video (native VP9) and convert it to a USM file.",
        allow_abbrev=False,
    )
    parser.add_argument("url", help="YouTube video URL.")
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output .usm file path. Defaults to <title>.usm in current directory.",
    )
    parser.add_argument(
        "-q", "--quality",
        type=str,
        default=DEFAULT_QUALITY,
        help=f"yt-dlp format selector (default: {DEFAULT_QUALITY}).",
    )
    parser.add_argument(
        "-k", "--key",
        type=str,
        default=None,
        help="Hex or decimal encryption key for the USM (e.g. 0x1234abcd).",
    )
    parser.add_argument(
        "--ffmpeg-dir",
        type=str,
        default=str(DEFAULT_FFMPEG_DIR),
        help=f"Directory containing ffmpeg.exe / ffprobe.exe (default: {DEFAULT_FFMPEG_DIR}).",
    )
    parser.add_argument(
        "--encoding",
        type=str,
        default=DEFAULT_ENCODING,
        help=f"Character encoding for the USM (default: {DEFAULT_ENCODING}).",
    )
    parser.add_argument(
        "--keep-intermediate",
        action="store_true",
        help="Keep the downloaded .webm and .ivf files after conversion.",
    )
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Disable automatic cleanup of the temporary download directory.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv if argv is None else argv)

    try:
        yt_dlp_to_usm(
            url=args.url,
            output=args.output,
            key=args.key,
            encoding=args.encoding,
            keep_intermediate=args.keep_intermediate,
            no_cleanup=args.no_cleanup,
        )
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
