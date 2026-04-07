#!/usr/bin/env python3
"""
Bird flashcard pipeline:
1. Scan all images for QR codes
2. Fetch each URL, extract title + audio file
3. Download audio files named after the bird
4. Write manifest.json for the flashcard app
"""

import json
import re
import sys
from pathlib import Path

import cv2
import requests
from bs4 import BeautifulSoup

IMAGES_DIR = Path(__file__).parent.parent
OUTPUT_DIR = Path(__file__).parent.parent / "audio"
MANIFEST_PATH = Path(__file__).parent.parent / "manifest.json"

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; BirdFlashcard/1.0)"}


# ── Step 1: scan all images ──────────────────────────────────────────────────

def scan_images(images_dir: Path) -> list[str]:
    detector = cv2.wechat_qrcode_WeChatQRCode()
    urls: list[str] = []
    seen: set[str] = set()

    jpg_files = sorted(images_dir.glob("PXL_*.jpg"))
    print(f"Found {len(jpg_files)} image(s) to scan.")

    for img_path in jpg_files:
        img = cv2.imread(str(img_path))
        results, _ = detector.detectAndDecode(img)
        new = [r for r in results if r and r not in seen]
        for r in new:
            seen.add(r)
            urls.append(r)
        print(f"  {img_path.name}: {len(results)} QR code(s), {len(new)} new  → total {len(urls)}")

    print(f"\nTotal unique QR codes found: {len(urls)}")
    return urls


# ── Step 2: fetch page, extract title + audio ─────────────────────────────────

def fetch_bird_info(url: str) -> dict | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"  [ERROR] {url}: {e}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # Try common heading selectors, fall back to <title>
    name = None
    for selector in ["h1", "h2", ".page-title", ".article-title", "title"]:
        tag = soup.select_one(selector)
        if tag and tag.get_text(strip=True):
            name = tag.get_text(strip=True)
            break

    if not name:
        print(f"  [WARN] No title found for {url}")
        name = url.rstrip("/").split("/")[-1]

    # Find audio element or link ending in .mp3/.ogg/.wav
    audio_url = None
    audio_tag = soup.find("audio")
    if audio_tag:
        src = audio_tag.get("src") or (audio_tag.find("source") or {}).get("src")
        if src:
            audio_url = src

    if not audio_url:
        for a in soup.find_all("a", href=True):
            if re.search(r"\.(mp3|ogg|wav)(\?|$)", a["href"], re.I):
                audio_url = a["href"]
                break

    if not audio_url:
        # scan all src attributes across the page
        for tag in soup.find_all(src=True):
            if re.search(r"\.(mp3|ogg|wav)(\?|$)", tag["src"], re.I):
                audio_url = tag["src"]
                break

    if not audio_url:
        print(f"  [WARN] No audio found for {url} ({name})")

    # Make absolute
    if audio_url and not audio_url.startswith("http"):
        from urllib.parse import urljoin
        audio_url = urljoin(url, audio_url)

    return {"name": name, "url": url, "audio_url": audio_url}


# ── Step 3: download audio ────────────────────────────────────────────────────

def safe_filename(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*]', "", name)
    name = re.sub(r"\s+", "_", name.strip())
    return name


def download_audio(bird: dict, output_dir: Path) -> str | None:
    if not bird["audio_url"]:
        return None

    ext = re.search(r"\.(mp3|ogg|wav)", bird["audio_url"], re.I)
    ext = ext.group(0).lower() if ext else ".mp3"
    filename = safe_filename(bird["name"]) + ext
    dest = output_dir / filename

    if dest.exists():
        print(f"  [SKIP] {filename} already exists")
        return filename

    try:
        resp = requests.get(bird["audio_url"], headers=HEADERS, timeout=30, stream=True)
        resp.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                f.write(chunk)
        print(f"  [OK]   {filename}")
        return filename
    except Exception as e:
        print(f"  [ERROR] downloading {bird['audio_url']}: {e}")
        return None


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    print("=" * 60)
    print("STEP 1: Scanning images for QR codes")
    print("=" * 60)
    urls = scan_images(IMAGES_DIR)

    print("\n" + "=" * 60)
    print("STEP 2: Fetching bird pages")
    print("=" * 60)
    birds = []
    for i, url in enumerate(urls, 1):
        print(f"[{i}/{len(urls)}] {url}")
        info = fetch_bird_info(url)
        if info:
            birds.append(info)
            print(f"       name='{info['name']}'  audio={info['audio_url']}")

    print("\n" + "=" * 60)
    print("STEP 3: Downloading audio files")
    print("=" * 60)
    for bird in birds:
        bird["audio_file"] = download_audio(bird, OUTPUT_DIR)

    print("\n" + "=" * 60)
    print("STEP 4: Writing manifest.json")
    print("=" * 60)
    manifest = [
        {"name": b["name"], "url": b["url"], "audio_file": b["audio_file"]}
        for b in birds
        if b["audio_file"]
    ]
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(f"Wrote {len(manifest)} entries to {MANIFEST_PATH}")

    missing = [b["name"] for b in birds if not b["audio_file"]]
    if missing:
        print(f"\n[WARN] {len(missing)} bird(s) with no audio: {missing}")

    print("\nDone!")


if __name__ == "__main__":
    main()
