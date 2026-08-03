"""
PNG to USM CLI

Convert a single PNG image into a looping VP9 IVF video, then wrap it into a
Criware USM file using Wannacri.

Usage:
    python png_to_usm.py <input.png> <duration_seconds> [-o output.usm] [--key 0x...]

Example:
    python png_to_usm.py E:\\SONG_BG1868.png 210 -o F:\\path\\to\\pv_1868.usm
"""

from __future__ import annotations

import argparse
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
from typing import Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_FFMPEG = shutil.which("ffmpeg") or "ffmpeg"
DEFAULT_ENCODING = "shift-jis"
FPS = 1  # low frame rate keeps file size small for static images


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def create_ivf(png_path: str, duration: float, ivf_path: str, ffmpeg_exe: str = DEFAULT_FFMPEG) -> None:
    """Create a single-frame looping VP9 IVF video from a PNG."""
    cmd = [
        ffmpeg_exe,
        "-y",
        "-loop", "1",
        "-t", str(duration),
        "-framerate", str(FPS),
        "-i", png_path,
        "-c:v", "libvpx-vp9",
        "-pix_fmt", "yuv420p",
        "-an",
        "-f", "ivf",
        ivf_path,
    ]
    print(f"FFmpeg: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR: FFmpeg failed (exit {result.returncode}):")
        print(result.stderr)
        sys.exit(1)
    print(f"  IVF written: {ivf_path}")


def convert_to_usm(ivf_path: str, output_path: pathlib.Path, key: Optional[int] = None, encoding: str = DEFAULT_ENCODING) -> None:
    """Convert an IVF file to USM using Wannacri."""
    from wannacri.codec import Sofdec2Codec
    from wannacri.usm import Usm, Vp9, OpMode

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Probe & verify codec
    codec = Sofdec2Codec.from_file(ivf_path)
    if codec is not Sofdec2Codec.VP9:
        print(f"ERROR: Expected VP9/IVF but got {codec}.")
        sys.exit(1)

    # 2. Build the Vp9 container
    video = Vp9(ivf_path)

    # 3. Wrap in a Usm
    usm = Usm(videos=[video], audios=None, key=key, version=16777984)

    # 4. Pick the operation mode
    mode = OpMode.NONE if key is None else OpMode.ENCRYPT

    # 5. Stream packets to disk
    with open(output_path, "wb") as f:
        for packet in usm.stream(mode, encoding=encoding):
            f.write(packet)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a PNG image into a looping VP9 USM video.",
        allow_abbrev=False,
    )
    parser.add_argument("png", help="Path to the input PNG image.")
    parser.add_argument("duration", type=float, help="Video duration in seconds.")
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output .usm file path.",
    )
    parser.add_argument(
        "-k", "--key",
        type=str,
        default=None,
        help="Hex or decimal encryption key (e.g. 0x1234abcd).",
    )
    parser.add_argument(
        "--ffmpeg",
        type=str,
        default=DEFAULT_FFMPEG,
        help=f"Path to ffmpeg executable (default: {DEFAULT_FFMPEG}).",
    )
    parser.add_argument(
        "--encoding",
        type=str,
        default=DEFAULT_ENCODING,
        help=f"Character encoding for the USM (default: {DEFAULT_ENCODING}).",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv if argv is None else argv)

    png_path = args.png
    duration = args.duration
    ffmpeg_exe = args.ffmpeg

    # Parse the key argument (hex or decimal)
    parsed_key: Optional[int] = None
    if args.key is not None:
        parsed_key = int(args.key, 0)

    if not os.path.exists(png_path):
        print(f"ERROR: PNG not found: {png_path}")
        return 1

    # Use a temp file for IVF
    with tempfile.TemporaryDirectory(prefix="png_to_usm_") as tmpdir:
        ivf_path = os.path.join(tmpdir, "video.ivf")

        # --- Step 1: Create VP9 IVF from PNG ---
        print(f"Creating VP9 IVF ({duration}s, {FPS}fps) from {png_path}...")
        create_ivf(png_path, duration, ivf_path, ffmpeg_exe)

        # --- Step 2: Convert to USM ---
        if args.output:
            output_path = pathlib.Path(args.output)
        else:
            base = pathlib.Path(png_path).stem
            output_path = pathlib.Path.cwd() / f"{base}.usm"

        print(f"Converting to USM (output: {output_path})...")
        convert_to_usm(ivf_path, output_path, parsed_key, args.encoding)
        size_kb = os.path.getsize(output_path) / 1024
        print(f"Done. USM written to: {output_path} ({size_kb:.1f} KB)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
