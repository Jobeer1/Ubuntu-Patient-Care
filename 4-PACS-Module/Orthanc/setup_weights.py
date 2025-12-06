#!/usr/bin/env python3
"""
Orthanc/setup_weights.py

Safely prepare Whisper model weights for the hackathon/demo.

Behavior:
- By default the script will create small placeholder files under
  medical-reporting-module/models/whisper so the repository remains
  lightweight and pushable.
- Use --download to attempt to download the real files from the
  configured URLs (network required). The script will stream the
  download and show progress.

This keeps large model files out of git history while making it
straightforward for judges to fetch the real weights if needed.
"""

from __future__ import annotations

import argparse
import os
import sys
import urllib.request
from pathlib import Path
from typing import Iterable, Tuple


def ensure_dirs(paths: Iterable[Path]) -> None:
    for p in paths:
        p.mkdir(parents=True, exist_ok=True)


def create_placeholder(path: Path, text: str = "# Placeholder model file\n") -> None:
    if path.exists():
        print(f"✅ Already exists: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        # write a tiny placeholder (text) so the repo doesn't contain the large binary
        path.write_text(text, encoding="utf-8")
        print(f"✅ Created placeholder: {path}")
    except Exception as exc:
        print(f"❌ Failed to create placeholder {path}: {exc}")


def download_file(url: str, dest: Path, chunk_size: int = 16_384) -> bool:
    """Download a URL to dest (stream) with a simple progress indicator.

    Returns True on success, False on failure.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(url) as resp:
            total = resp.getheader("Content-Length")
            total = int(total) if total and total.isdigit() else None
            downloaded = 0
            # write to a temporary file first
            tmp = dest.with_suffix(dest.suffix + ".part")
            with open(tmp, "wb") as out:
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    out.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        percent = int(downloaded * 100 / total)
                        sys.stdout.write(f"\rDownloading {dest.name}: {percent}%")
                    else:
                        sys.stdout.write(f"\rDownloading {dest.name}: {downloaded} bytes")
                    sys.stdout.flush()
            # move into place
            tmp.replace(dest)
            sys.stdout.write("\n")
        print(f"✅ Downloaded: {dest}")
        return True
    except Exception as exc:
        print(f"\n❌ Error downloading {url} -> {dest}: {exc}")
        # cleanup partial file if present
        try:
            part = dest.with_suffix(dest.suffix + ".part")
            if part.exists():
                part.unlink()
        except Exception:
            pass
        return False


def setup_model_weights(download: bool = False, force: bool = False) -> bool:
    """Prepare model files: placeholders by default, optional real downloads.

    Returns True on success (placeholders created or downloads succeeded),
    False on unrecoverable errors.
    """
    root = Path(__file__).parent
    os.chdir(root)

    models_dir = Path("medical-reporting-module") / "models" / "whisper"
    cache_dir = models_dir / "cache"
    ensure_dirs([models_dir, cache_dir])

    print("🚀 Setting up Ubuntu Patient Care - Model Weights")
    print("=" * 60)

    # Small manifest of files we expect. URLs are provided as examples.
    manifest: Tuple[Tuple[str, str, Path], ...] = (
        (
            "whisper-base",
            "https://huggingface.co/openai/whisper-base/resolve/main/pytorch_model.bin",
            models_dir / "base.pt",
        ),
        (
            "whisper-medium-cache",
            "https://example.com/path/to/medium_temp.pt",
            cache_dir / "medium_temp.pt",
        ),
    )

    # Create placeholders or download depending on flags
    overall_ok = True
    for name, url, path in manifest:
        if path.exists() and not force:
            print(f"✅ Exists: {path}")
            continue

        if download:
            print(f"📥 Downloading {name} from {url} -> {path}")
            ok = download_file(url, path)
            if not ok:
                print(f"⚠️  Download failed for {name}; creating placeholder instead.")
                create_placeholder(path)
                overall_ok = False
        else:
            print(f"⚠️  Not downloading {name} (use --download to enable); creating placeholder")
            create_placeholder(path)

    print("\n🎉 Setup finished.")
    print("\n📝 Next steps for judges / demo runners:")
    print(" - The repository intentionally contains small placeholder files so the git repo stays lightweight.")
    print(" - To use real voice/ASR features, download the real model files and replace the placeholders:")
    for _, url, path in manifest:
        print(f"   * {path} <- {url}")
    print(" - You can re-run this script with --download to attempt automatic fetches (network required).")
    print(" - Alternatively host the large weights on Google Drive/OneDrive/S3 and update the URLs in this script.")

    return overall_ok


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Prepare Whisper model weights (placeholders by default)")
    p.add_argument("--download", action="store_true", help="Attempt to download the real model files")
    p.add_argument("--force", action="store_true", help="Overwrite existing files if present")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    ok = setup_model_weights(download=args.download, force=args.force)
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
