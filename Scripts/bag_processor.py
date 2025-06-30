#!C:\Program Files\Python313\python.exe
"""Bag pattern tiling + Photoshop automation for Bag 1–3 templates.

This script is invoked by *Scripts/images.py* after the regular wrapping-paper
Photoshop pass.  It performs three steps:

1. Locate the most-recent Download folder created earlier in the run.
2. Build 3 × 3 tiled versions ( *_3.png* ) of every original design image it
   finds there (the 6 × 6 tiles already exist from the main pipeline).
3. Launch Photoshop with *bags.jsx* which applies each tile to Bag 1, Bag 2 and
   Bag 3 PSD templates and exports *_bag1.png*, *_bag2.png* & *_bag3.png* files
   into the matching Output/<timestamp>/ folder.

The script is intentionally self-contained so failures here never abort the
wrapping-paper workflow – *images.py* treats a non-zero exit as non-fatal.
"""

from __future__ import annotations

import subprocess
import sys
import os
import logging
from pathlib import Path
from typing import List

from PIL import Image  # Pillow is already listed in requirements

# Re-use the shared config constants so we always point at the right folders
try:
    from config import DOWNLOAD_BASE_FOLDER, OUTPUT_BASE_FOLDER
except ImportError:
    # Fallback for unit-test environments where config may not be importable
    DOWNLOAD_BASE_FOLDER = str(Path(__file__).resolve().parent.parent / "Download")
    OUTPUT_BASE_FOLDER = str(Path(__file__).resolve().parent.parent / "Output")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

PHOTOSHOP_EXE_CANDIDATES = [
    r"C:\\Program Files\\Adobe\\Adobe Photoshop 2025\\Photoshop.exe",
    r"C:\\Program Files\\Adobe\\Adobe Photoshop 2024\\Photoshop.exe",
    r"C:\\Program Files\\Adobe\\Adobe Photoshop 2023\\Photoshop.exe",
    r"C:\\Program Files (x86)\\Adobe\\Adobe Photoshop 2025\\Photoshop.exe",
    r"C:\\Program Files (x86)\\Adobe\\Adobe Photoshop 2024\\Photoshop.exe",
    r"C:\\Program Files (x86)\\Adobe\\Adobe Photoshop 2023\\Photoshop.exe",
]


def _most_recent_subfolder(base: Path) -> Path | None:
    """Return the newest YYYY-MM-DD_HH-MM-SS sub-folder under *base*."""
    if not base.exists():
        return None
    candidates = [p for p in base.iterdir() if p.is_dir() and len(p.name) == 19 and p.name[4] == "-" and p.name[7] == "-"]
    if not candidates:
        return None
    return sorted(candidates, key=lambda p: p.name, reverse=True)[0]


def _create_3x3_tiles(download_folder: Path) -> List[Path]:
    """Create *_3.png* tiles (3 × 3) beside every original PNG in *download_folder*."""
    originals = [p for p in download_folder.iterdir() if p.suffix.lower() == ".png" and not p.name.endswith("_6.png") and not p.name.endswith("_3.png")]
    logger.info("Found %d original PNGs", len(originals))
    created: List[Path] = []
    for src in originals:
        dest = src.with_name(src.stem + "_3.png")
        try:
            with Image.open(src) as img:
                w, h = img.size
                tiled = Image.new(img.mode, (w * 3, h * 3))
                for y in range(3):
                    for x in range(3):
                        tiled.paste(img, (x * w, y * h))
                tiled.save(dest)
                created.append(dest)
                logger.info("Created 3×3 tile: %s", dest.name)
        except Exception as e:
            logger.error("Failed to create 3×3 tile for %s: %s", src.name, e)
    return created


def _find_photoshop() -> str | None:
    for p in PHOTOSHOP_EXE_CANDIDATES:
        if os.path.exists(p):
            return p
    return None


def _run_bag_jsx(script_dir: Path) -> bool:
    jsx_path = script_dir / "bags.jsx"
    if not jsx_path.exists():
        logger.error("bags.jsx not found at %s", jsx_path)
        return False
    photoshop_exe = _find_photoshop()
    if not photoshop_exe:
        logger.error("Photoshop executable not found – cannot run bag JSX")
        return False
    logger.info("Running bags.jsx via Photoshop…")
    proc = subprocess.Popen([photoshop_exe, "-r", str(jsx_path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        stdout, stderr = proc.communicate(timeout=600)  # 10 min
        if stdout:
            logger.debug(stdout.decode(errors="replace"))
        if stderr:
            logger.error(stderr.decode(errors="replace"))
    except subprocess.TimeoutExpired:
        logger.error("bags.jsx timed-out, terminating Photoshop")
        proc.kill()
        return False
    return proc.returncode == 0


def process_bags() -> bool:
    logger.info("Bag-processing step starting…")
    script_dir = Path(__file__).resolve().parent
    download_base = Path(DOWNLOAD_BASE_FOLDER)
    output_base = Path(OUTPUT_BASE_FOLDER)

    recent_download = _most_recent_subfolder(download_base)
    recent_output = _most_recent_subfolder(output_base)

    if not recent_download or not recent_output:
        logger.error("Could not locate recent Download or Output sub-folders – skipping bags")
        return False

    logger.info("Using Download folder %s", recent_download)
    _create_3x3_tiles(recent_download)

    jsx_ok = _run_bag_jsx(script_dir)
    if jsx_ok:
        logger.info("BAG_PROCESSING_COMPLETE")
    else:
        logger.error("Bag JSX processing failed")
    return jsx_ok


if __name__ == "__main__":
    ok = process_bags()
    sys.exit(0 if ok else 1) 