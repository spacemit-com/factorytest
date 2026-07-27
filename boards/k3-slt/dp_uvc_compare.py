#!/usr/bin/env python3
"""
Display-to-UVC loopback comparison test.

Topology:
  DUT DP output -> DP-to-HDMI converter -> HDMI capture card -> DUT USB UVC input

The test displays a generated full-screen reference pattern on DP, captures one
frame from the UVC device with ffmpeg, and compares the capture with the
reference image using ffmpeg's SSIM filter.
"""

from __future__ import annotations

import argparse
import glob
import re
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path


SSIM_RE = re.compile(r"All:\s*([0-9.]+)")


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    print("+ " + " ".join(shlex.quote(part) for part in cmd))
    proc = subprocess.run(cmd, text=True, capture_output=True)
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="", file=sys.stderr)
    if check and proc.returncode != 0:
        raise RuntimeError(f"command failed with exit code {proc.returncode}: {cmd[0]}")
    return proc


def require_tool(path_or_name: str) -> str:
    if Path(path_or_name).exists():
        return path_or_name
    resolved = shutil.which(path_or_name)
    if not resolved:
        raise RuntimeError(f"required tool not found in PATH: {path_or_name}")
    return resolved


def parse_size(size: str) -> tuple[int, int]:
    if size == "auto":
        return detect_display_size()
    match = re.fullmatch(r"(\d+)x(\d+)", size)
    if not match:
        raise argparse.ArgumentTypeError("size must use WIDTHxHEIGHT or auto")
    return int(match.group(1)), int(match.group(2))


def detect_display_size() -> tuple[int, int]:
    candidates = [
        Path("/sys/class/graphics/fb0/virtual_size"),
        Path("/sys/class/graphics/fb0/modes"),
    ]
    for candidate in candidates:
        if not candidate.exists():
            continue
        text = candidate.read_text(encoding="utf-8", errors="ignore").strip().splitlines()[0]
        comma_match = re.search(r"(\d+)\s*,\s*(\d+)", text)
        mode_match = re.search(r"(\d+)x(\d+)", text)
        match = comma_match or mode_match
        if match:
            width, height = int(match.group(1)), int(match.group(2))
            if width > 0 and height > 0:
                print(f"detected display size: {width}x{height} from {candidate}")
                return width, height

    drm_modes = sorted(glob.glob("/sys/class/drm/*-DP-*/modes"))
    drm_modes += sorted(glob.glob("/sys/class/drm/*-HDMI-*/modes"))
    drm_modes += sorted(glob.glob("/sys/class/drm/*/modes"))
    for mode_file in drm_modes:
        text = Path(mode_file).read_text(encoding="utf-8", errors="ignore").strip().splitlines()
        for line in text:
            match = re.search(r"(\d+)x(\d+)", line)
            if match:
                width, height = int(match.group(1)), int(match.group(2))
                if width > 0 and height > 0:
                    print(f"detected display size: {width}x{height} from {mode_file}")
                    return width, height

    raise RuntimeError("could not auto-detect display size; pass --size WIDTHxHEIGHT")


def generate_reference(ffmpeg: str, output: Path, size: str) -> None:
    # testsrc2 has hard edges, color bars, and fine detail that make cable/capture
    # errors easier to spot than a flat color screen.
    run(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "warning",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"testsrc2=size={size}:rate=1",
            "-frames:v",
            "1",
            "-update",
            "1",
            str(output),
        ]
    )


def list_video_devices() -> list[tuple[str, str]]:
    devices: list[tuple[str, str]] = []
    def video_index(path: str) -> int:
        match = re.search(r"video(\d+)$", path)
        return int(match.group(1)) if match else 9999

    for sys_path in sorted(glob.glob("/sys/class/video4linux/video*"), key=video_index):
        name_path = Path(sys_path) / "name"
        name = name_path.read_text(encoding="utf-8", errors="ignore").strip() if name_path.exists() else ""
        devices.append((f"/dev/{Path(sys_path).name}", name))
    if devices:
        return devices
    return [(device, "") for device in sorted(glob.glob("/dev/video*"))]


def resolve_uvc_device(device: str) -> str:
    if device != "auto":
        return device

    devices = list_video_devices()
    if not devices:
        raise RuntimeError("could not find any /dev/video* device")

    skip_terms = ("csi", "isp", "mvx")
    preferred_terms = ("uvc", "hdmi", "capture", "usb3 video", "usb video", "usb3")
    for node, name in devices:
        lowered = name.lower()
        if any(term in lowered for term in skip_terms):
            continue
        if any(term in lowered for term in preferred_terms):
            print(f"detected UVC device: {node} ({name})")
            return node

    usable_devices = [
        (node, name)
        for node, name in devices
        if not any(term in name.lower() for term in skip_terms)
    ]
    node, name = usable_devices[0] if usable_devices else devices[0]
    print(f"using first video device: {node} ({name or 'unknown'})")
    return node


def resolve_input_format(ffmpeg: str, device: str, input_format: str | None) -> str | None:
    if input_format != "auto":
        return input_format

    proc = run([ffmpeg, "-hide_banner", "-f", "v4l2", "-list_formats", "all", "-i", device], check=False)
    formats = (proc.stdout + proc.stderr).lower()
    if "yuyv422" in formats:
        print("detected UVC input format: yuyv422")
        return "yuyv422"
    if "mjpeg" in formats:
        print("detected UVC input format: mjpeg")
        return "mjpeg"
    print("could not detect preferred UVC input format; letting ffmpeg choose")
    return None


def start_display(display_command: str, reference: Path) -> subprocess.Popen[str] | None:
    if not display_command:
        return None
    command = display_command.format(reference=str(reference))
    args = shlex.split(command)
    print("+ " + " ".join(shlex.quote(part) for part in args))
    return subprocess.Popen(args, text=True)


def capture_uvc(
    ffmpeg: str,
    device: str,
    output: Path,
    size: str,
    input_format: str | None,
    framerate: str | None,
) -> None:
    cmd = [ffmpeg, "-hide_banner", "-loglevel", "warning", "-y", "-f", "v4l2"]
    if input_format:
        cmd += ["-input_format", input_format]
    if size:
        cmd += ["-video_size", size]
    if framerate:
        cmd += ["-framerate", framerate]
    cmd += ["-i", device, "-frames:v", "1", "-update", "1", str(output)]
    run(cmd)


def compare_ssim(
    ffmpeg: str,
    reference: Path,
    capture: Path,
    diff: Path,
    width: int,
    height: int,
    stats_file: Path,
) -> float:
    filter_graph = (
        f"[1:v]scale={width}:{height}:flags=bicubic,format=yuv420p[captured];"
        "[0:v]format=yuv420p[reference];"
        f"[reference][captured]ssim=stats_file={stats_file}"
    )
    proc = run(
        [
            ffmpeg,
            "-hide_banner",
            "-y",
            "-i",
            str(reference),
            "-i",
            str(capture),
            "-lavfi",
            filter_graph,
            "-f",
            "null",
            "-",
        ]
    )
    combined_output = proc.stdout + proc.stderr
    match = SSIM_RE.search(combined_output)
    if not match:
        raise RuntimeError("could not parse SSIM score from ffmpeg output")

    diff_filter = (
        f"[1:v]scale={width}:{height}:flags=bicubic[captured];"
        "[0:v][captured]blend=all_mode=difference,"
        "eq=brightness=0.04:contrast=8"
    )
    run(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "warning",
            "-y",
            "-i",
            str(reference),
            "-i",
            str(capture),
            "-lavfi",
            diff_filter,
            "-frames:v",
            "1",
            "-update",
            "1",
            str(diff),
        ]
    )
    return float(match.group(1))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare DP output content with UVC capture-card content."
    )
    parser.add_argument("--device", default="auto", help="UVC V4L2 node, default: auto")
    parser.add_argument("--size", default="auto", help="capture/display size, default: auto")
    parser.add_argument("--input-format", default="auto", help="ffmpeg v4l2 input format, for example mjpeg")
    parser.add_argument("--framerate", default=None, help="optional UVC frame rate, for example 30")
    parser.add_argument("--threshold", type=float, default=0.90, help="minimum SSIM pass score")
    parser.add_argument("--settle-seconds", type=float, default=10.0, help="wait after showing the pattern")
    parser.add_argument("--workdir", default="artifacts/dp_uvc_compare", help="output directory")
    parser.add_argument("--ffmpeg", default="ffmpeg", help="ffmpeg path")
    parser.add_argument("--ffplay", default="ffplay", help="ffplay path")
    parser.add_argument(
        "--reference-image",
        default=None,
        help="use an existing reference image instead of generating one with ffmpeg",
    )
    parser.add_argument(
        "--display-only",
        action="store_true",
        help="only show the reference image; do not capture or compare UVC data",
    )
    parser.add_argument(
        "--display-seconds",
        type=float,
        default=0,
        help="seconds to keep the reference displayed in --display-only mode; 0 waits until interrupted",
    )
    parser.add_argument(
        "--display-command",
        default=None,
        help="command used to show the reference; use {reference} as placeholder",
    )
    parser.add_argument(
        "--no-display",
        action="store_true",
        help="do not start a viewer; assume the reference is already displayed",
    )
    args = parser.parse_args()

    width, height = parse_size(args.size)
    size = f"{width}x{height}"
    workdir = Path(args.workdir)
    workdir.mkdir(parents=True, exist_ok=True)

    reference = Path(args.reference_image) if args.reference_image else workdir / f"reference_{size}.bmp"
    capture = workdir / f"uvc_capture_{size}.bmp"
    diff = workdir / f"diff_{size}.bmp"
    stats_file = workdir / "ssim.log"

    try:
        ffmpeg = require_tool(args.ffmpeg) if not args.reference_image else args.ffmpeg
        ffplay = require_tool(args.ffplay) if not args.no_display else args.ffplay
        if args.reference_image:
            if not reference.exists():
                raise RuntimeError(f"reference image does not exist: {reference}")
        else:
            generate_reference(ffmpeg, reference, size)

        display_command = args.display_command
        if display_command is None and not args.no_display:
            display_command = f"{ffplay} -hide_banner -loglevel error -fs -loop 0 {{reference}}"

        viewer = start_display(display_command or "", reference)
        try:
            if args.display_only:
                print(f"displaying reference: {reference}")
                if args.display_seconds > 0:
                    time.sleep(args.display_seconds)
                elif viewer:
                    viewer.wait()
                return 0
            if not args.no_display:
                time.sleep(args.settle_seconds)
            ffmpeg = require_tool(args.ffmpeg)
            device = resolve_uvc_device(args.device)
            input_format = resolve_input_format(ffmpeg, device, args.input_format)
            capture_uvc(ffmpeg, device, capture, size, input_format, args.framerate)
        finally:
            if viewer and viewer.poll() is None:
                viewer.terminate()
                try:
                    viewer.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    viewer.kill()

        score = compare_ssim(ffmpeg, reference, capture, diff, width, height, stats_file)
        print(f"SSIM All={score:.6f}, threshold={args.threshold:.6f}")
        print(f"reference: {reference}")
        print(f"capture:   {capture}")
        print(f"diff:      {diff}")
        if score >= args.threshold:
            print("result: successful")
            return 0
        print("result: failed")
        return 1
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
